# -*- coding: utf-8 -*-
# Author: mertaygn, cglrgrkn
"""PEMF SAHTE SUNUCU — ana PEMF sunucusunun YERİNE geçer: Kontrol ve Simülasyon sekmelerinin kullandığı uçları AYNI biçimde konuşur.

Ne yapar:
  - 7 bobinli PEMF cihazını YAZILIMDA canlandırır (çalışıyor / frekans / duty / faz / süre, seans ve kalan süre, ACİL DURDUR mandalı).
    Ölçüm ÜRETMEZ: bobin kartlarında ölçüm alanları boş kalır (gerçek cihazda akım / MLX ölçümü gelir).
  - `--modul <kimlik>` verilirse bobin komutlarını SİZİN sürücünüze (`moduller/<kimlik>/surucu.py`) iletir: ilk bobin başlayınca
    `uygula` + `baslat`, son bobin durunca `durdur`, ACİL DURDUR'da `acil_durdur` (sürücü ana uygulamadaki gibi AYRI SÜREÇTE koşar,
    500 ms kalp atışı alır). `--sahte-kart` şablon modülün sahte kartını da başlatır (kartsız deneme).
  - Canlı alan haritası: gerçek kalibre alan modeli kitte YOKTUR; harita SENTETİK dipollerden üretilir (kalibrasyon kimliği
    "sentetik-kit"). Biçim gerçek sunucunun `alan_haritasi` sürüm 1 iletisiyle aynıdır.
  - `/simulator/` altında dijital ikizi (`--ikiz <klasör>`), `/` altında derlenmiş arayüzü (`uygulama/dist`) sunar.

Çalıştırma (depo kökünde):  python sunucu/sahte_sunucu.py  [--port 8765] [--modul sablon --sahte-kart] [--ikiz ornek-ikiz]
Sonra tarayıcıda http://127.0.0.1:8765 (önce `cd uygulama && npm run export:web`). Ayrıntı: README.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import json
import logging
import math
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

logger = logging.getLogger("sahte_sunucu")

BOBIN_SAYISI = 7  # ana cihaz: 7 STM bobini (arayüzdeki tek kaynak `STM_BOBIN_SAYISI` ile aynı)
BIPOLAR_YETENEKLI = (1, 2, 3, 4, 5)  # ana cihazda bobin 6-7 sürücüsü tek yönlü (yalnız unipolar)
YAYIN_ARALIK_S = 1.0
VARSAYILAN_PORT = 8765

# ── Sentetik alan haritası (gerçek modelin YERİNE; değerler gerçek kabini temsil etmez) ─────────────────────────────────────────────
CAM_IC_MM = (
    555.0,
    350.0,
    405.0,
)  # kabin cam içi: X genişlik (+X önden bakanın SOLU), Y yükseklik (+Y yukarı), Z derinlik (+Z arkaya)
ADIM_MM = 20.0
KADEME, YOK = 254, 255
#: sentetik bobin merkezleri (kabin çerçevesi, mm) ve dipol yönleri — 5 taban + 2 yan
_MERKEZ = (
    (-150, -215, -110),
    (0, -215, -110),
    (150, -215, -110),
    (-150, -215, 110),
    (150, -215, 110),
    (-310, 0, 0),
    (310, 0, 0),
)
_YON = ((0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0), (1, 0, 0), (-1, 0, 0))
_OLCEK_MT = 2.4e6  # 50 % duty'de taban ortası ~1 mT mertebesi (sentetik)


def _izgara():
    boyut = [int(math.floor(c / ADIM_MM + 1e-9)) + 1 for c in CAM_IC_MM]
    kok = [-(b - 1) / 2.0 * ADIM_MM for b in boyut]
    return kok, boyut


def sentetik_harita(calisanlar: list[dict]) -> dict:
    """Çalışan bobinler [{bobin, frekans, duty, faz}] → `alan_haritasi` sürüm 1 verisi (durum `tamam` ya da `sifir`)."""
    kok, boyut = _izgara()
    temel = {"surum": 1, "zaman": time.time(), "modelTahmini": True}
    if not calisanlar:
        return {**temel, "durum": "sifir"}
    t0 = time.perf_counter()
    nx, ny, nz = boyut
    tepe = [0.0] * (nx * ny * nz)
    for ix in range(nx):
        x = kok[0] + ix * ADIM_MM
        for iy in range(ny):
            y = kok[1] + iy * ADIM_MM
            for iz in range(nz):
                z = kok[2] + iz * ADIM_MM
                bx = by = bz = 0.0
                for c in calisanlar:
                    mx, my, mz = _MERKEZ[c["bobin"] - 1]
                    ux, uy, uz = _YON[c["bobin"] - 1]
                    rx, ry, rz = x - mx, y - my, z - mz
                    d = math.sqrt(rx * rx + ry * ry + rz * rz) + 60.0
                    rx, ry, rz = rx / d, ry / d, rz / d
                    mr = rx * ux + ry * uy + rz * uz
                    k = _OLCEK_MT * (c["duty"] / 50.0) / (d * d * d)
                    bx += (3 * mr * rx - ux) * k
                    by += (3 * mr * ry - uy) * k
                    bz += (3 * mr * rz - uz) * k
                tepe[(ix * ny + iy) * nz + iz] = math.sqrt(bx * bx + by * by + bz * bz)
    enb = max(tepe)
    olcek = enb / KADEME if enb > 0 else 0.0
    kod = bytes(min(KADEME, int(round(v / olcek))) if olcek > 0 else 0 for v in tepe)
    i = max(range(len(tepe)), key=tepe.__getitem__)
    ix, rem = divmod(i, ny * nz)
    iy, iz = divmod(rem, nz)
    return {
        **temel,
        "durum": "tamam",
        "kalibrasyon": "sentetik-kit",
        "izgara": {"kok": kok, "adim": ADIM_MM, "boyut": boyut, "cerceve": "kabin", "camIc": list(CAM_IC_MM)},
        "deger": base64.b64encode(kod).decode("ascii"),
        "olcek": olcek,
        "yok": YOK,
        "enYuksek": {
            "mT": round(enb, 4),
            "konum": [kok[0] + ix * ADIM_MM, kok[1] + iy * ADIM_MM, kok[2] + iz * ADIM_MM],
        },
        "bobinler": calisanlar,
        "uyarilar": [],
        "hesapMs": round((time.perf_counter() - t0) * 1000.0, 1),
    }


# ── Sürücü köprüsü (isteğe bağlı) ─────────────────────────────────────────────────────────────────────────────────────────────────────
class ModulKoprusu:
    """Bobin komutlarını geliştiricinin sürücüsüne iletir (ana uygulamanın modül yöneticisiyle — `servers/modul_yonetici.py`)."""

    def __init__(self, kimlik: str):
        os.environ.setdefault("PEMF_MODULLER_KOKU", str(KOK / "moduller"))
        from servers import modul_kayit, modul_yonetici

        self._hata_sinifi = modul_kayit.ModulHatasi
        _, self.modul = modul_kayit.bul(kimlik)
        # Üründe modüller varsayılan GİZLİ (Ayarlar anahtarı); kitte geliştiricinin kendi modülü görünür — ayar kitin veri klasörüne yazılır
        # (`.veri/`, `PEMF_KIT_VERI`), gerçek uygulamanın ayarına DOKUNULMAZ.
        modul_kayit.gorunur_yaz(True)
        self.yonetici = modul_yonetici.yonetici()
        self.yonetici.sec(kimlik)
        self.kimlik = kimlik

    def _guvenli(self, islev, *a):
        try:
            islev(*a)
            return None
        except self._hata_sinifi as e:
            return f"{e.kod}{(' · ' + e.alan) if e.alan else ''}"

    def calistir(self, frekans: float, duty: float, sure_dk: float):
        sinirlar = self.modul["sinirlar"]
        ayar = {k: v for k, v in (("frekans_hz", frekans), ("duty_yuzde", duty), ("sure_dk", sure_dk)) if k in sinirlar}
        return self._guvenli(self.yonetici.uygula, ayar) or self._guvenli(self.yonetici.baslat)

    def durdur(self):
        return self._guvenli(self.yonetici.durdur)

    def acil(self) -> None:
        self.yonetici.acil_durdur_hepsi()

    def kapat(self) -> None:
        with contextlib.suppress(Exception):
            self.yonetici.birak()


# ── Cihaz benzetimi ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class Cihaz:
    """7 bobin + seans + ACİL DURDUR mandalı. Bütün değişiklikler kilit altında; yayınlar olay döngüsünden yapılır."""

    def __init__(self, modul: ModulKoprusu | None = None):
        self.kilit = threading.RLock()
        self.modul = modul
        self.bobinler = {
            i: {
                "running": False,
                "frequencyHz": 0.0,
                "dutyCycle": 0.0,
                "phase": 0.0,
                "bitis": None,
                "unipolarIstek": False,
            }
            for i in range(1, BOBIN_SAYISI + 1)
        }
        self.seans: dict | None = None
        self.seans_no = 0
        self.mandal = {"aktif": False, "nesil": 0}
        self.bildirimler: list[dict] = []
        self._bildirim_no = 0
        self.olaylar: list[dict] = []  # yayınlanacak anlık iletiler (emergency_stop, estop_mandali, notification …)
        # Sürücü çağrıları AYRI iş parçacığında, sırayla: takılan bir sürücü HTTP yanıtlarını ve ACİL DURDUR'u BEKLETMEZ.
        self._isler: queue.Queue = queue.Queue()
        if modul is not None:
            threading.Thread(target=self._isci, daemon=True, name="modul-isci").start()

    def _isci(self) -> None:
        while True:
            islem, a = self._isler.get()
            if islem == "calistir":
                with self.kilit:
                    mandal = self.mandal["aktif"]
                if mandal:  # ACİL DURDUR mandalı kuruluyken karta BAŞLAT gitmez
                    continue
                hata = self.modul.calistir(*a)
                with self.kilit:
                    mandal = self.mandal["aktif"]
                if (
                    mandal
                ):  # başlatma uçuştayken ACİL DURDUR geldi → kart yeniden açılmış olabilir: bir kez daha ACİL DURDUR
                    self.modul.acil()
            else:
                hata = self.modul.durdur()
            if hata:
                with self.kilit:
                    self._bildir(f"Sürücü hatası: {hata}", f"Driver error: {hata}")

    # ── yardımcılar ──
    def _bildir(self, tr: str, en: str, seviye: str = "warning") -> None:
        self._bildirim_no += 1
        n = {
            "id": self._bildirim_no,
            "message": tr,
            "mesajlar": {"tr": tr, "en": en},
            "level": seviye,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "read": False,
        }
        self.bildirimler = [n, *self.bildirimler][:50]
        self.olaylar.append({"type": "notification", "data": n})

    def _calisan_var(self) -> bool:
        return any(b["running"] for b in self.bobinler.values())

    def _modul_sonrasi(self, once_calisiyordu: bool, frekans: float = 0, duty: float = 0, sure_dk: float = 0) -> None:
        """Bobin kümesi boştan doluya / doludan boşa geçince sürücüye iletilecek işi KUYRUĞA koy (hata → bildirim, arayüzde görünür)."""
        if self.modul is None:
            return
        simdi = self._calisan_var()
        if simdi and not once_calisiyordu:
            self._isler.put(("calistir", (frekans, duty, sure_dk)))
        elif once_calisiyordu and not simdi:
            self._isler.put(("durdur", ()))

    def _bobin_baslat(self, i: int, f: float, d: float, faz: float, sure_s: float) -> None:
        b = self.bobinler[i]
        b.update(
            running=True,
            frequencyHz=float(f),
            dutyCycle=float(d),
            phase=float(faz),
            bitis=(time.time() + sure_s) if sure_s and sure_s > 0 else None,
        )

    def _bobin_durdur(self, i: int) -> None:
        self.bobinler[i].update(running=False, bitis=None)

    # ── uçların işleri ──
    def snapshot(self) -> dict:
        with self.kilit:
            stm = "online"
            coils = []
            for i, b in self.bobinler.items():
                coils.append(
                    {
                        "id": i,
                        "connected": True,
                        "running": b["running"],
                        "frequencyHz": b["frequencyHz"],
                        "dutyCycle": b["dutyCycle"],
                        "phase": b["phase"],
                        "magneticMt": 0,
                        "objectTemp": 0,
                        "ambientTemp": 0,
                        "currentA": 0,
                        "stm32Driven": True,
                        "measuredFields": [],
                        # sürüş kipi: yetenek + istek → etkin (firmware kuralı `etkin = yeteneksiz || istek`)
                        "bipolarYetenek": i in BIPOLAR_YETENEKLI,
                        "unipolarIstek": b["unipolarIstek"],
                        "unipolar": (i not in BIPOLAR_YETENEKLI) or b["unipolarIstek"],
                        "durationMin": (round(max(0.0, b["bitis"] - time.time()) / 60.0, 2) if b["bitis"] else None),
                    }
                )
            return {
                "gateway": "online",
                "mqtt": "offline",
                "espEtkin": False,
                "internet": "offline",
                "stm": stm,
                "patient": {"name": "", "species": "", "breed": "", "owner": ""},
                "activeTreatment": self.aktif_tedavi(),
                "coils": coils,
                "sessions": [],
                "notifications": list(self.bildirimler),
                "system": {
                    "softwareVersion": "sahte-sunucu 0.1",
                    "hardwareVersion": "benzetim",
                    "deviceId": "sahte",
                    "totalSessions": self.seans_no,
                    "uptime": "—",
                    "startTime": time.strftime("%Y-%m-%dT%H:%M:%S"),
                },
                "eField": None,
                "estopMandali": dict(self.mandal),
                "estopTeyit": None,
                "stmUyum": {"uyumlu": True},
                "akimOlcumu": False,
            }

    def aktif_tedavi(self) -> dict:
        s = self.seans
        if not s:
            return {
                "mode": "Sistem Hazır",
                "frequencyHz": 0,
                "intensityMt": 0,
                "remainingMin": 0,
                "elapsedSec": 0,
                "durationSec": 0,
                "isActive": False,
            }
        gecen = time.time() - s["baslangic"]
        kalan = max(0.0, s["sure_s"] - gecen)
        return {
            "mode": s["mode"],
            "frequencyHz": s["frequency"],
            "intensityMt": s["intensity"],
            "remainingMin": kalan / 60.0,
            "elapsedSec": int(gecen),
            "durationSec": int(s["sure_s"]),
            "isActive": True,
        }

    def seans_aktif(self) -> dict:
        with self.kilit:
            s = self.seans
            if not s:
                return {"is_active": False}
            gecen = time.time() - s["baslangic"]
            return {
                "is_active": True,
                "mode": s["mode"],
                "frequency": s["frequency"],
                "intensity": s["intensity"],
                "duration_minutes": s["sure_s"] / 60.0,
                "elapsed_sec": int(gecen),
                "remaining_sec": int(max(0.0, s["sure_s"] - gecen)),
                "db_session_id": s["no"],
            }

    def seans_baslat(self, g: dict):
        with self.kilit:
            if self.mandal["aktif"]:
                return 409, {
                    "detail": "ACİL DURDUR mandalı kurulu — önce Sıfırla. / EMERGENCY STOP latch is set — reset first."
                }
            if self.seans:
                return 409, {"detail": "Etkin seans var. / A session is already active."}
            bobinler = [int(i) for i in (g.get("coil_ids") or []) if 1 <= int(i) <= BOBIN_SAYISI]
            if not bobinler:
                return 400, {"detail": "Bobin seçilmedi. / No coil selected."}
            dk = float(g.get("duration_minutes") or 20)
            once = self._calisan_var()
            for i in bobinler:
                self._bobin_baslat(i, g.get("frequency") or 0, g.get("duty") or 0, g.get("phase") or 0, dk * 60)
            self.seans_no += 1
            self.seans = {
                "no": self.seans_no,
                "mode": str(g.get("mode") or "Manuel"),
                "frequency": float(g.get("frequency") or 0),
                "intensity": float(g.get("intensity") or 0),
                "sure_s": dk * 60,
                "baslangic": time.time(),
                "bobinler": bobinler,
            }
            self._modul_sonrasi(once, float(g.get("frequency") or 0), float(g.get("duty") or 0), dk)
            return 200, {"status": "success", "session": {"db_session_id": self.seans_no}}

    def seans_durdur(self) -> dict:
        with self.kilit:
            once = self._calisan_var()
            if self.seans:
                for i in self.seans["bobinler"]:
                    self._bobin_durdur(i)
            self.seans = None
            self._modul_sonrasi(once)
            return {"status": "success"}

    def parametre_guncelle(self, g: dict) -> dict:
        with self.kilit:
            if not self.seans:
                return {"status": "error", "detail": "Etkin seans yok. / No active session."}
            self.seans["frequency"] = float(g.get("frequency") or self.seans["frequency"])
            if g.get("duration_minutes"):
                self.seans["sure_s"] = float(g["duration_minutes"]) * 60
            return {"status": "success"}

    def bobin_komutu(self, ids: list[int], g: dict) -> list[dict]:
        with self.kilit:
            once = self._calisan_var()
            sonuc = []
            for i in ids:
                if not 1 <= i <= BOBIN_SAYISI:
                    sonuc.append({"coil_id": i, "status": "invalid"})
                    continue
                if g.get("start"):
                    if self.mandal["aktif"]:
                        sonuc.append(
                            {
                                "coil_id": i,
                                "status": "estop_latched",
                                "mesaj": "ACİL DURDUR mandalı kurulu — önce Sıfırla.",
                            }
                        )
                        continue
                    self._bobin_baslat(
                        i, g.get("freq") or 0, g.get("duty") or 0, g.get("phase") or 0, float(g.get("duration") or 0)
                    )
                else:
                    self._bobin_durdur(i)
                sonuc.append({"coil_id": i, "status": "success", "command_id": uuid.uuid4().hex})
            self._modul_sonrasi(
                once, float(g.get("freq") or 0), float(g.get("duty") or 0), float(g.get("duration") or 0) / 60.0
            )
            return sonuc

    def acil_durdur(self) -> dict:
        # Sürücüye ACİL DURDUR kilitten ÖNCE ve bağımsız gider (takılı bir istek onu bekletmez — ana uygulamadaki kural).
        if self.modul is not None:
            threading.Thread(target=self.modul.acil, daemon=True, name="modul-acil").start()
            with contextlib.suppress(queue.Empty):
                while True:  # bekleyen sürücü işleri (BAŞLAT dahil) atılır
                    self._isler.get_nowait()
        with self.kilit:
            calisiyordu = self._calisan_var() or self.seans is not None
            for i in self.bobinler:
                self._bobin_durdur(i)
            self.seans = None
            self.mandal = {
                "aktif": True,
                "neden": "ACİL DURDUR",
                "zaman": time.time(),
                "nesil": self.mandal.get("nesil", 0) + 1,
                "eylemSifirlaSoyler": False,
            }
            self.olaylar.append({"type": "emergency_stop", "data": {"zaman": time.time()}})
            self.olaylar.append({"type": "estop_mandali", "data": dict(self.mandal)})
            return {
                "confirmed": True,
                "status": "success",
                "stmStopped": True,
                "stmKartYaniti": "kabul",
                "calisiyordu": calisiyordu,
            }

    def mandal_sifirla(self) -> dict:
        with self.kilit:
            self.mandal = {"aktif": False, "sifirlamaZamani": time.time(), "nesil": self.mandal.get("nesil", 0)}
            self.olaylar.append({"type": "estop_mandali", "data": dict(self.mandal)})
            return {"status": "success"}

    def surus_kipi(self, unipolar: list) -> dict:
        with self.kilit:
            for i, u in enumerate(unipolar[:BOBIN_SAYISI], start=1):
                self.bobinler[i]["unipolarIstek"] = bool(u) or i not in BIPOLAR_YETENEKLI
            return {
                "status": "success",
                "etkin": [
                    (i not in BIPOLAR_YETENEKLI) or self.bobinler[i]["unipolarIstek"]
                    for i in range(1, BOBIN_SAYISI + 1)
                ],
            }

    def tik(self) -> None:
        """Süre doldu mu? (bobin ve seans) — saniyede bir."""
        with self.kilit:
            once = self._calisan_var()
            simdi = time.time()
            for i, b in self.bobinler.items():
                if b["running"] and b["bitis"] and simdi >= b["bitis"]:
                    self._bobin_durdur(i)
            if self.seans and simdi - self.seans["baslangic"] >= self.seans["sure_s"]:
                for i in self.seans["bobinler"]:
                    self._bobin_durdur(i)
                self.seans = None
            self._modul_sonrasi(once)

    def calisanlar(self) -> list[dict]:
        with self.kilit:
            return [
                {"bobin": i, "frekans": b["frequencyHz"], "duty": b["dutyCycle"], "faz": b["phase"]}
                for i, b in self.bobinler.items()
                if b["running"]
            ]


# ── Uygulama ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
_IKIZ_YOK = """<!doctype html><meta charset="utf-8"><body style="background:#121827;color:#F7FAFC;font:15px system-ui;padding:24px">
<h3>Dijital ikiz yok / No digital twin</h3>
<p>Sahte sunucuyu <code>--ikiz &lt;klasör&gt;</code> ile başlatın (klasörde <code>index.html</code> olmalı).</p>
<p>Start the fake server with <code>--ikiz &lt;folder&gt;</code> (the folder must contain <code>index.html</code>).</p></body>"""


def uygulama_kur(cihaz: Cihaz, ikiz: Path | None = None, arayuz: Path | None = None) -> FastAPI:
    @contextlib.asynccontextmanager
    async def omur(_app):
        gorev = asyncio.create_task(yayinci())
        try:
            yield
        finally:
            gorev.cancel()
            if cihaz.modul is not None:
                cihaz.modul.kapat()

    app = FastAPI(title="PEMF sahte sunucu", lifespan=omur)
    # Geliştirme sunucusundan (expo start --web, ör. :8081) gelen isteklere izin — yalnız bu bilgisayar.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],
    )
    istemciler: set[WebSocket] = set()
    aboneler: set[WebSocket] = set()
    durum = {"harita_anahtar": None, "harita": None}

    def j(kod: int, govde: dict):
        return JSONResponse(status_code=kod, content=govde)

    @app.get("/api/health")
    def saglik():
        return {"status": "ok", "sahte": True}

    @app.get("/api/dashboard-snapshot")
    def anlik():
        return cihaz.snapshot()

    @app.get("/api/session/active")
    def seans_aktif():
        return cihaz.seans_aktif()

    @app.post("/api/session/start")
    def seans_baslat(g: dict = Body(default={})):
        return j(*cihaz.seans_baslat(g))

    @app.post("/api/session/stop")
    def seans_durdur(g: dict = Body(default={})):
        return cihaz.seans_durdur()

    @app.post("/api/session/parametre_guncelle")
    def parametre(g: dict = Body(default={})):
        return cihaz.parametre_guncelle(g)

    @app.post("/api/hardware/emergency_stop")
    def acil():
        return cihaz.acil_durdur()

    @app.post("/api/hardware/command")
    def komut(g: dict = Body(default={})):
        if g.get("command") == "stop_all_coils":
            cihaz.bobin_komutu(list(range(1, BOBIN_SAYISI + 1)), {"start": False})
            return {"status": "success"}
        return j(400, {"detail": "Bilinmeyen komut. / Unknown command."})

    @app.post("/api/hardware/estop_mandali/sifirla")
    def sifirla(g: dict = Body(default={})):
        if g.get("onay") is not True:
            return j(400, {"detail": "Onay gerekli. / Confirmation required."})
        return cihaz.mandal_sifirla()

    @app.post("/api/hardware/auto_preset")
    def oneri(g: dict = Body(default={})):
        # Ana uygulamanın literatür tablosu kitte YOK — her hedef için genel varsayılan döner ("default_wellness" rozeti görünür).
        return {"parameters": {"freq": 50, "duty": 25, "duration": 20, "intensity": 1.0, "source": "default_wellness"}}

    @app.post("/api/coil/batch")
    def toplu(g: dict = Body(default={})):
        return {"status": "success", "results": cihaz.bobin_komutu([int(i) for i in g.get("coil_ids") or []], g)}

    @app.post("/api/coil/surus_kipi")
    def surus(g: dict = Body(default={})):
        return cihaz.surus_kipi(list(g.get("unipolar") or []))

    @app.post("/api/coil/{bobin}/control")
    def tek(bobin: int, g: dict = Body(default={})):
        r = cihaz.bobin_komutu([bobin], g)[0]
        return {k: v for k, v in r.items() if k != "coil_id"}

    @app.get("/api/sahte/modul")
    def modul_durumu():
        """Hata ayıklama (yalnız kit): sürücünün bildirdiği durum — ör. şablonda `{"bobin": true, "ayar": {...}}`."""
        if cihaz.modul is None:
            return {"modul": None}
        try:
            return {"modul": cihaz.modul.kimlik, **cihaz.modul.yonetici.durum()}
        except cihaz.modul._hata_sinifi as e:
            return j(503, {"modul": cihaz.modul.kimlik, "hata": e.kod})

    @app.post("/api/notifications/clear")
    def temizle():
        with cihaz.kilit:
            cihaz.bildirimler = []
        return {"status": "success"}

    @app.websocket("/ws")
    async def ws(soket: WebSocket):
        await soket.accept()
        istemciler.add(soket)
        try:
            await soket.send_json({"type": "snapshot", "data": cihaz.snapshot()})
            while True:
                m = json.loads(await soket.receive_text())
                if m.get("type") == "ping":
                    await soket.send_json({"type": "pong"})
                elif m.get("type") == "alan_abone":
                    (aboneler.add if m.get("acik") else aboneler.discard)(soket)
        except (WebSocketDisconnect, RuntimeError, ValueError):
            pass
        finally:
            istemciler.discard(soket)
            aboneler.discard(soket)

    async def gonder(ileti: dict, alicilar) -> None:
        for s in list(alicilar):
            try:
                await s.send_json(ileti)
            except Exception:  # noqa: BLE001 — kopan istemci yayını durdurmaz
                istemciler.discard(s)
                aboneler.discard(s)

    async def yayinci():
        while True:
            await asyncio.sleep(YAYIN_ARALIK_S)
            await asyncio.to_thread(cihaz.tik)
            with cihaz.kilit:
                olaylar, cihaz.olaylar = cihaz.olaylar, []
            for o in olaylar:
                await gonder(o, istemciler)
            await gonder({"type": "snapshot", "data": cihaz.snapshot()}, istemciler)
            at = cihaz.aktif_tedavi()
            if at["isActive"]:
                await gonder({"type": "session_tick", "data": at}, istemciler)
            if aboneler:
                calisan = cihaz.calisanlar()
                anahtar = json.dumps(calisan, sort_keys=True)
                if anahtar != durum["harita_anahtar"]:
                    durum["harita"] = await asyncio.to_thread(sentetik_harita, calisan)
                    durum["harita_anahtar"] = anahtar
                await gonder({"type": "alan_haritasi", "data": durum["harita"]}, aboneler)

    if ikiz is not None and (ikiz / "index.html").is_file():
        app.mount("/simulator", StaticFiles(directory=str(ikiz), html=True), name="ikiz")
    else:

        @app.get("/simulator/index.html")
        @app.get("/simulator/")
        def ikiz_yok():
            return HTMLResponse(_IKIZ_YOK)

    if arayuz is not None and (arayuz / "index.html").is_file():
        app.mount("/", StaticFiles(directory=str(arayuz), html=True), name="arayuz")
    return app


def sahte_karti_baslat(kimlik: str) -> subprocess.Popen:
    """Modülün sahte kartını AYRI süreçte başlatır (kartsız deneme). Boru adı `modul.json`daki `baglanti_ayrinti.boru`; sürücü
    aynı adı `PEMF_<KİMLİK>_BORU` ortam değişkeninden alır (şablon sürücüdeki kural)."""
    klasor = KOK / "moduller" / kimlik
    m = json.loads((klasor / "modul.json").read_text(encoding="utf-8"))
    boru = (m.get("baglanti_ayrinti") or {}).get("boru") or f"pemf-{kimlik}-kart"
    os.environ["PEMF_" + kimlik.upper().replace("-", "_") + "_BORU"] = boru
    return subprocess.Popen(
        [sys.executable, str(klasor / "sahte_kart.py"), "--boru", boru, "--bekci-ms", str(m.get("bekci_ms", 1500))],
        cwd=str(KOK),
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="PEMF sahte sunucu (geliştirici kiti)")
    p.add_argument("--port", type=int, default=VARSAYILAN_PORT)
    p.add_argument("--modul", help="bobin komutlarını iletecek modül kimliği (moduller/<kimlik>)")
    p.add_argument("--sahte-kart", action="store_true", help="modülün sahte_kart.py'sini de başlat (kartsız deneme)")
    p.add_argument("--ikiz", help="Simülasyon sekmesinde açılacak dijital ikiz klasörü (index.html içeren)")
    p.add_argument(
        "--arayuz", default=str(KOK / "uygulama" / "dist"), help="derlenmiş arayüz klasörü (npm run export:web)"
    )
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    kart = None
    if a.sahte_kart and a.modul:
        kart = sahte_karti_baslat(a.modul)
        time.sleep(0.8)
    try:
        modul = ModulKoprusu(a.modul) if a.modul else None
        app = uygulama_kur(Cihaz(modul), Path(a.ikiz).resolve() if a.ikiz else None, Path(a.arayuz).resolve())
        import uvicorn

        print(f"PEMF sahte sunucu: http://127.0.0.1:{a.port}  (durdurmak için Ctrl+C)")
        uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="warning")
    finally:
        if kart is not None:
            kart.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
