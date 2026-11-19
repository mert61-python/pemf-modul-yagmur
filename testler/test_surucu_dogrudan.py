# -*- coding: utf-8 -*-
"""Sürücünüzü SÜREÇ İÇİNDE (sahte karta karşı) bütün kollarıyla sürer — CI'daki sürücü kapsamı %100 ölçüsü bunu sayar (kabul testlerinde
sürücü ayrı süreçte koştuğu için kapsam ölçülemez). Kendi kartınıza geçince hata kollarını kendi kartınızın davranışıyla güncelleyin."""

import importlib.util
import os
import subprocess
import sys
import threading
import uuid

import pytest
from conftest import KIT, MODUL

KLASOR = KIT / "moduller" / MODUL


@pytest.fixture
def kart():
    ad = f"pemf-kit-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    p = subprocess.Popen(
        [sys.executable, "-X", "utf8", str(KLASOR / "sahte_kart.py"), "--boru", ad, "--bekci-ms", "1500"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    hazir = threading.Event()
    threading.Thread(target=lambda: (p.stdout.readline(), hazir.set()), daemon=True).start()
    assert hazir.wait(30)
    yield ad, p
    p.kill()
    p.wait(10)


def _surucu(ad, monkeypatch):
    from servers.modul_surucu import surucuyu_yukle

    monkeypatch.setenv("PEMF_" + MODUL.upper().replace("-", "_") + "_BORU", ad)
    return surucuyu_yukle(str(KLASOR))


def test_SURUCU_butun_kollar(kart, monkeypatch):
    from servers.modul_surucu import SurucuHatasi

    ad, p = kart
    s = _surucu(ad, monkeypatch)
    with pytest.raises(SurucuHatasi) as e:
        s.kalp()  # bağlanmadan
    assert e.value.kod == "bagliDegil"
    s.baglan()
    s.uygula({"frekans_hz": 100, "duty_yuzde": 25})
    s.baslat()
    s.kalp()
    assert s.durum() == {"bobin": True, "ayar": {"frekans_hz": 100, "duty_yuzde": 25}}
    s.durdur()
    s.acil_durdur()
    with pytest.raises(SurucuHatasi) as e:
        s._gonder({"k": "hata"})  # kart reddetti
    assert e.value.kod == "kartHatasi"
    with pytest.raises(SurucuHatasi) as e:
        s.uygula({"frekans_hz": 9999})  # kartın KENDİ sınırı
    assert e.value.kod == "kartSinirDisi"
    with pytest.raises(SurucuHatasi) as e:
        s._gonder({"k": "uyu", "sn": 1.0})  # yavaş kart → zaman aşımı, takılmaz
    assert e.value.kod == "kartYanitsiz"
    s.kes()
    s.kes()  # ikinci kesme zararsız
    s.baglan()
    p.kill()
    p.wait(10)
    with pytest.raises(SurucuHatasi) as e:
        s.kalp()  # bağlantı koptu
    assert e.value.kod == "baglantiKoptu"


def test_SURUCU_kart_YOKSA_bulunamadi(monkeypatch):
    from servers.modul_surucu import SurucuHatasi

    s = _surucu(f"pemf-kit-yok-{uuid.uuid4().hex[:8]}", monkeypatch)
    with pytest.raises(SurucuHatasi) as e:
        s.baglan()
    assert e.value.kod == "kartBulunamadi"


def test_SURUCU_adres_POSIX(monkeypatch):
    spec = importlib.util.spec_from_file_location("_kit_surucu", KLASOR / "surucu.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m.sys, "platform", "linux")
    adr, aile = m._adres("x")
    assert aile == "AF_UNIX" and adr.endswith("x.sock")
