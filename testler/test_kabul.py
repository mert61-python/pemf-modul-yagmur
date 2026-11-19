# -*- coding: utf-8 -*-
# Author: mertaygn, cglrgrkn
"""KİT KABUL TESTLERİ (ana depodaki `tests/test_GA_B4_ornek_modul_KABUL.py` ile AYNI ölçüler; HTTP / sunucu açılışı testleri ana depoda).
GERÇEK süreçler: kartınız (ya da sahte kart — `moduller/<kimlik>/sahte_kart.py`, ayrı süreç) + sürücünüz `--alt-surec modul-surucu` alt sürecinde.

  A1 `acil_durdur_hepsi` dönüşü ≤ 50 ms · kart ≤ 100 ms içinde keser
  A2 kalp atışı akarken bobin açık kalır; kesilince kart bekçisi bobini KENDİSİ keser
  A3 sınır dışı ayar SUNUCUDA reddedilir — karta HİÇ gitmez; ayarsız kart başlamaz
  A4 ebeveyn bağlantıyı keserse (stdin kapanır) sürücü ÖNCE acil_durdur → bobin durur
  B6 sürücü çökünce sunucu ayakta + kart durur
Gerçek kartla: sahte kart fikstürünü kendi kartınızın durum okumasıyla değiştirin (kart `durum` → bobin / kapanma zamanı / neden).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid

import pytest

from conftest import KIT, MODUL

KOK = KIT
KART = KOK / "moduller" / MODUL / "sahte_kart.py"


def _olcum(ad: str, deger: float) -> None:
    yol = os.environ.get("GA_KABUL_OLCUM")
    if yol:
        with open(yol, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"olcum": ad, "ms": round(deger * 1000.0, 2)}) + "\n")


def _kart_istemci(ad: str):
    sys.path.insert(0, str(KART.parent))
    try:
        import sahte_kart
    finally:
        sys.path.remove(str(KART.parent))
    from multiprocessing.connection import Client

    adr, aile = sahte_kart.adres(ad)
    return Client(adr, family=aile, authkey=sahte_kart.ANAHTAR)


@pytest.fixture
def kart(monkeypatch):
    """Sahte kart AYRI süreçte; sürücü alt süreci boru adını `PEMF_ORNEK_BORU`'dan alır."""
    from utils import gizli_surec

    ad = f"pemf-ga-test-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    p = gizli_surec.baslat(
        [sys.executable, "-X", "utf8", str(KART), "--boru", ad, "--bekci-ms", "1500"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    hazir = threading.Event()
    threading.Thread(target=lambda: (p.stdout.readline(), hazir.set()), daemon=True).start()
    assert hazir.wait(30), "sahte kart açılmadı"
    monkeypatch.setenv("PEMF_" + MODUL.upper().replace("-", "_") + "_BORU", ad)
    from servers import modul_kayit

    monkeypatch.setattr(modul_kayit, "gorunur_mu", lambda: True)
    baglanti = _kart_istemci(ad)

    def durum():
        baglanti.send({"k": "durum"})
        return baglanti.recv()

    yield durum
    baglanti.close()
    p.kill()
    p.wait(10)


@pytest.fixture
def yonetici():
    from servers.modul_yonetici import ModulYoneticisi

    y = ModulYoneticisi()
    yield y
    y.birak()


def _calistir(y, durum):
    y.sec(MODUL)
    y.uygula({"frekans_hz": 100, "duty_yuzde": 25})
    y.baslat()
    assert durum()["bobin"] is True


def _bekle(kosul, sure):
    t0 = time.monotonic()
    while time.monotonic() - t0 < sure:
        if kosul():
            return True
        time.sleep(0.005)
    return False


def test_KABUL_A1_ACIL_DURDUR_donus_50ms_KART_100ms(kart, yonetici):
    _calistir(yonetici, kart)
    assert yonetici.durum()["surucu"] == {"bobin": True, "ayar": {"frekans_hz": 100, "duty_yuzde": 25}}
    t_duvar = time.time()
    t0 = time.perf_counter()
    sonuc = yonetici.acil_durdur_hepsi()
    donus = time.perf_counter() - t0
    assert sonuc == [{"kimlik": MODUL, "onay": True}]
    assert donus <= 0.05, donus
    d = kart()
    assert d["bobin"] is False and d["kapanma"]["neden"] == "acil"
    kesme = d["kapanma"]["zaman"] - t_duvar
    assert kesme <= 0.1, kesme
    _olcum("acil_donus", donus)
    _olcum("kart_kesme", kesme)


def test_KABUL_A2_KALP_kesilince_KART_kendisi_keser(kart, yonetici):
    _calistir(yonetici, kart)
    time.sleep(3.2)  # kalp atışı akarken bobin AÇIK kalır (bekçi 1500 ms, kalp 500 ms)
    assert kart()["bobin"] is True
    t0 = time.time()
    yonetici._kalp_dur.set()  # sunucunun kalp atışı kesildi (donma / kablo)
    assert _bekle(lambda: kart()["bobin"] is False, 3.0)
    d = kart()
    assert d["kapanma"]["neden"] == "bekci"
    gecikme = d["kapanma"]["zaman"] - t0
    assert gecikme <= 1.5 + 0.5 + 0.3, gecikme  # bekçi + son kalbin yaşı + pay
    _olcum("bekci_kesme", gecikme)


def test_KABUL_A3_SINIR_DISI_ayar_karta_GITMEZ(kart, yonetici):
    from servers.modul_kayit import ModulHatasi

    yonetici.sec(MODUL)
    for ayar, kod in (
        ({"frekans_hz": 9999}, "ayarSinirDisi"),
        ({"guc_w": 5}, "ayarBilinmeyen"),
        ({"duty_yuzde": "50"}, "ayarSayiDegil"),
    ):
        with pytest.raises(ModulHatasi) as e:
            yonetici.uygula(ayar)
        assert e.value.kod == kod
    assert kart()["ayar"] == {}  # karta HİÇBİRİ gitmedi
    with pytest.raises(ModulHatasi) as e:
        yonetici.baslat()  # ayarsız kart başlamaz (kart kuralı)
    assert (e.value.kod, e.value.alan) == ("surucuHatasi", "ayarYok")
    assert kart()["bobin"] is False


def test_KABUL_A4_EBEVEYN_gidince_bobin_DURUR(kart, yonetici):
    _calistir(yonetici, kart)
    p = yonetici._etkin[2]._p
    p.stdin.close()  # ana sunucu öldü / bağlantı koptu
    assert _bekle(lambda: kart()["bobin"] is False, 3.0)
    assert kart()["kapanma"]["neden"] == "acil"  # kabuk ÖNCE acil_durdur çağırdı
    assert _bekle(lambda: p.poll() is not None, 5.0)


def test_KABUL_B6_surucu_COKUNCE_sunucu_AYAKTA_kart_DURUR(kart, yonetici):
    from servers.modul_kayit import ModulHatasi

    _calistir(yonetici, kart)
    yonetici._etkin[2]._p.kill()
    assert _bekle(lambda: kart()["bobin"] is False, 2.0)  # bağlantı koptu → kart keser
    with pytest.raises(ModulHatasi) as e:
        yonetici.durum()
    assert e.value.kod == "surucuOldu"
    t0 = time.perf_counter()
    assert yonetici.acil_durdur_hepsi() == []  # canlı süreç yok → anında
    assert time.perf_counter() - t0 < 0.05
