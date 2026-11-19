# -*- coding: utf-8 -*-
# Author: mertaygn, cglrgrkn
"""SAHTE SUNUCU testleri — arayüzün beklediği uçlar / iletiler, ACİL DURDUR mandalı, sentetik alan haritası, sürücü köprüsü.

Sahte sunucu ana PEMF sunucusunun YERİNE geçer; buradaki biçimler ana uygulamanın Kontrol sekmesinin okuduklarıdır. Değiştirirseniz
arayüz de etkilenir. Sürücü köprüsü kuralları (ACİL DURDUR beklemez, mandal kuruluyken karta BAŞLAT gitmez) ürün kurallarıdır.
"""

from __future__ import annotations

import base64
import threading
import time

import pytest
from fastapi.testclient import TestClient

from conftest import MODUL
from sunucu import sahte_sunucu as ss
from test_kabul import kart  # noqa: F401 — sahte kart fikstürü (ayrı süreç)


def _istemci(cihaz=None):
    return TestClient(ss.uygulama_kur(cihaz or ss.Cihaz()))


def _bekle(kosul, sure=5.0):
    son = time.monotonic() + sure
    while time.monotonic() < son:
        if kosul():
            return True
        time.sleep(0.02)
    return False


SEANS = {"mode": "Manuel", "frequency": 100, "duty": 25, "phase": 0, "duration_minutes": 1, "coil_ids": [1, 2, 3]}


# ── uçlar ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_anlik_7_bobin_ve_surus_kipi_alanlari():
    with _istemci() as c:
        assert c.get("/api/health").json()["status"] == "ok"
        d = c.get("/api/dashboard-snapshot").json()
        assert [b["id"] for b in d["coils"]] == [1, 2, 3, 4, 5, 6, 7]
        assert d["stm"] == "online" and d["estopMandali"]["aktif"] is False
        b6 = d["coils"][5]
        assert b6["bipolarYetenek"] is False and b6["unipolar"] is True  # 6-7 tek yönlü
        assert d["coils"][0]["bipolarYetenek"] is True and d["coils"][0]["unipolar"] is False
        assert all(b["measuredFields"] == [] for b in d["coils"])  # ölçüm UYDURULMAZ


def test_seans_baslat_durdur_ve_tam_sayi_sureler():
    with _istemci() as c:
        assert c.post("/api/session/start", json=SEANS).json()["status"] == "success"
        a = c.get("/api/session/active").json()
        assert a["is_active"] and isinstance(a["elapsed_sec"], int) and isinstance(a["remaining_sec"], int)
        assert [b["running"] for b in c.get("/api/dashboard-snapshot").json()["coils"]][:4] == [True, True, True, False]
        assert c.post("/api/session/start", json=SEANS).status_code == 409  # etkin seans varken ikincisi yok
        assert c.post("/api/session/parametre_guncelle", json={"frequency": 150}).json()["status"] == "success"
        assert c.post("/api/session/stop", json={}).json()["status"] == "success"
        assert c.get("/api/session/active").json() == {"is_active": False}
        assert c.post("/api/session/start", json={**SEANS, "coil_ids": []}).status_code == 400
        assert c.post("/api/session/parametre_guncelle", json={}).json()["status"] == "error"


def test_bobin_komutlari_surus_kipi_oneri_ve_toplu_durdurma():
    with _istemci() as c:
        r = c.post(
            "/api/coil/batch",
            json={"coil_ids": [1, 9], "freq": 50, "duty": 20, "phase": 0, "duration": 60, "start": True},
        )
        assert [x["status"] for x in r.json()["results"]] == ["success", "invalid"]
        t = c.post(
            "/api/coil/2/control", json={"freq": 80, "duty": 30, "phase": 90, "duration": 0, "start": True}
        ).json()
        assert t["status"] == "success" and len(t["command_id"]) == 32
        assert (
            c.post("/api/hardware/command", json={"command": "stop_all_coils", "params": {}}).json()["status"]
            == "success"
        )
        assert not any(b["running"] for b in c.get("/api/dashboard-snapshot").json()["coils"])
        assert c.post("/api/hardware/command", json={"command": "x"}).status_code == 400
        k = c.post("/api/coil/surus_kipi", json={"unipolar": [True, False, False, False, False, False, False]}).json()
        assert k["etkin"] == [True, False, False, False, False, True, True]
        assert (
            c.post("/api/hardware/auto_preset", json={"target_condition": "Eklem Ağrısı"}).json()["parameters"][
                "source"
            ]
            == "default_wellness"
        )
        assert c.post("/api/notifications/clear").json()["status"] == "success"
        assert c.get("/api/sahte/modul").json() == {"modul": None}


def test_bobin_suresi_dolunca_durur():
    cihaz = ss.Cihaz()
    cihaz.bobin_komutu([1], {"start": True, "freq": 10, "duty": 10, "duration": 0.05})
    time.sleep(0.1)
    cihaz.tik()
    assert cihaz.bobinler[1]["running"] is False
    cihaz.seans_baslat({**SEANS, "duration_minutes": 0.001})
    time.sleep(0.1)
    cihaz.tik()
    assert cihaz.seans is None and not any(b["running"] for b in cihaz.bobinler.values())


def test_acil_durdur_mandal_baslatmayi_engeller_sifirla_onay_ister():
    with _istemci() as c:
        c.post("/api/session/start", json=SEANS)
        y = c.post("/api/hardware/emergency_stop").json()
        assert y["confirmed"] is True and y["calisiyordu"] is True and y["stmKartYaniti"] == "kabul"
        d = c.get("/api/dashboard-snapshot").json()
        assert d["estopMandali"]["aktif"] is True and not any(b["running"] for b in d["coils"])
        assert c.post("/api/session/start", json=SEANS).status_code == 409
        r = c.post(
            "/api/coil/1/control", json={"freq": 50, "duty": 20, "phase": 0, "duration": 60, "start": True}
        ).json()
        assert r["status"] == "estop_latched"
        assert c.post("/api/hardware/estop_mandali/sifirla", json={}).status_code == 400  # onaysız sıfırlanmaz
        assert c.post("/api/hardware/estop_mandali/sifirla", json={"onay": True}).json()["status"] == "success"
        assert c.post("/api/session/start", json=SEANS).json()["status"] == "success"


# ── canlı iletiler ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _ilk(ws, tur, azami=20):
    for _ in range(azami):
        m = ws.receive_json()
        if m["type"] == tur:
            return m
    raise AssertionError(f"{tur} gelmedi")


def test_ws_anlik_ping_alan_aboneligi_ve_acil_iletileri():
    with _istemci() as c, c.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "snapshot"
        ws.send_json({"type": "ping"})
        _ilk(ws, "pong")
        ws.send_json({"type": "alan_abone", "acik": True})
        assert _ilk(ws, "alan_haritasi")["data"]["durum"] == "sifir"
        c.post("/api/session/start", json=SEANS)
        assert _ilk(ws, "session_tick")["data"]["isActive"] is True
        h = None
        for _ in range(10):
            h = _ilk(ws, "alan_haritasi")["data"]
            if h["durum"] == "tamam":
                break
        assert h["durum"] == "tamam" and h["kalibrasyon"] == "sentetik-kit" and h["modelTahmini"] is True
        c.post("/api/hardware/emergency_stop")
        assert _ilk(ws, "emergency_stop")["type"] == "emergency_stop"
        assert _ilk(ws, "estop_mandali")["data"]["aktif"] is True
        ws.send_json({"type": "alan_abone", "acik": False})
        ws.send_text("bozuk")  # geçersiz ileti bağlantıyı kapatır, sunucu ayakta kalır
    with _istemci() as c:
        assert c.get("/api/health").status_code == 200


def test_sentetik_harita_bicimi():
    h = ss.sentetik_harita([{"bobin": 2, "frekans": 100.0, "duty": 25.0, "faz": 0.0}])
    assert h["surum"] == 1 and h["izgara"]["boyut"] == [28, 18, 21] and h["izgara"]["camIc"] == [555.0, 350.0, 405.0]
    kod = base64.b64decode(h["deger"])
    assert len(kod) == 28 * 18 * 21 and max(kod) == 254 and h["enYuksek"]["mT"] > 0
    assert h["enYuksek"]["konum"][1] < 0  # taban bobini → en yüksek değer tabana yakın
    assert ss.sentetik_harita([])["durum"] == "sifir"


def test_ikiz_yokken_bilgi_sayfasi_ve_ikiz_klasoru(tmp_path):
    with _istemci() as c:
        assert "Dijital ikiz yok" in c.get("/simulator/index.html").text
    (tmp_path / "index.html").write_text("<p>ikiz</p>", encoding="utf-8")
    arayuz = tmp_path / "dist"
    arayuz.mkdir()
    (arayuz / "index.html").write_text("<p>arayuz</p>", encoding="utf-8")
    with TestClient(ss.uygulama_kur(ss.Cihaz(), tmp_path, arayuz)) as c:
        assert c.get("/simulator/index.html").text == "<p>ikiz</p>"
        assert c.get("/").text == "<p>arayuz</p>"


# ── sürücü köprüsü (kuyruk + ACİL DURDUR kuralları; sahte köprüyle) ──────────────────────────────────────────────────────────────────
class SahteKopru:
    def __init__(self, hata=None):
        self.cagri: list[str] = []
        self.bekle: threading.Event | None = None
        self.basladi = threading.Event()
        self.hata = hata
        self.kimlik = "sahte"

    def calistir(self, f, d, dk):
        self.cagri.append("calistir")
        self.basladi.set()
        if self.bekle is not None:
            self.bekle.wait(5)
        return self.hata

    def durdur(self):
        self.cagri.append("durdur")
        return self.hata

    def acil(self):
        self.cagri.append("acil")

    def kapat(self):
        self.cagri.append("kapat")


def test_kopru_ilk_bobinde_calistir_son_bobinde_durdur():
    k = SahteKopru()
    cihaz = ss.Cihaz(k)
    cihaz.bobin_komutu([1], {"start": True, "freq": 50, "duty": 20, "duration": 60})
    cihaz.bobin_komutu([2], {"start": True, "freq": 50, "duty": 20, "duration": 60})
    cihaz.bobin_komutu([1, 2], {"start": False})
    assert _bekle(lambda: k.cagri == ["calistir", "durdur"])


def test_kopru_hatasi_bildirim_olur():
    cihaz = ss.Cihaz(SahteKopru(hata="kartYanitsiz"))
    cihaz.seans_baslat(SEANS)
    assert _bekle(lambda: any("kartYanitsiz" in n["message"] for n in cihaz.bildirimler))
    assert cihaz.bildirimler[0]["mesajlar"]["en"].startswith("Driver error")


def test_acil_durdur_kuyrugu_bosaltir_ve_ucustaki_baslatmadan_sonra_yeniden_acil():
    k = SahteKopru()
    k.bekle = threading.Event()
    cihaz = ss.Cihaz(k)
    cihaz.seans_baslat(SEANS)  # → calistir (uçuşta, bekliyor)
    assert k.basladi.wait(5)
    cihaz.seans_durdur()  # → durdur kuyrukta
    cihaz.bobin_komutu([4], {"start": True, "freq": 50, "duty": 20, "duration": 60})  # → calistir kuyrukta
    t0 = time.monotonic()
    cihaz.acil_durdur()  # uçuştaki iş BEKLETMEZ; kuyruk boşalır
    assert time.monotonic() - t0 < 0.2
    k.bekle.set()
    assert _bekle(lambda: k.cagri.count("acil") == 2)  # 1) ACİL DURDUR 2) uçuştaki başlatma bitince yeniden
    time.sleep(0.2)
    assert k.cagri.count("calistir") == 1 and "durdur" not in k.cagri  # kuyruktakiler ATILDI


def test_mandal_kuruluyken_kuyruktaki_baslat_karta_gitmez():
    k = SahteKopru()
    cihaz = ss.Cihaz(k)
    with cihaz.kilit:
        cihaz.mandal["aktif"] = True
    cihaz._isler.put(("calistir", (50, 20, 1)))
    time.sleep(0.2)
    assert k.cagri == []


# ── gerçek sürücü + sahte kart (ayrı süreçler) ─────────────────────────────────────────────────────────────────────────────────────────
def test_gercek_surucu_seansla_baslar_acil_durdurla_kart_durur(kart):  # noqa: F811
    kopru = ss.ModulKoprusu(MODUL)
    try:
        cihaz = ss.Cihaz(kopru)
        with TestClient(ss.uygulama_kur(cihaz)) as c:
            assert c.post("/api/session/start", json=SEANS).json()["status"] == "success"
            assert _bekle(lambda: kart()["bobin"] is True), "kart başlamadı"
            assert c.get("/api/sahte/modul").json()["modul"] == MODUL
            t0 = time.monotonic()
            c.post("/api/hardware/emergency_stop")
            assert _bekle(lambda: kart()["bobin"] is False, 1.0)
            assert time.monotonic() - t0 < 0.5
    finally:
        kopru.kapat()


def test_modul_yoksa_kopru_hata_verir():
    from servers import modul_kayit

    with pytest.raises(modul_kayit.ModulHatasi):
        ss.ModulKoprusu("olmayan-modul")
