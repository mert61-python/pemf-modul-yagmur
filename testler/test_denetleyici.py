# -*- coding: utf-8 -*-
"""Sürücü denetleyicisi (ana depodaki `servers/modul_denetleyici.py` — AYNI kural seti) + `modul.json` doğrulaması."""

from conftest import KIT, MODUL


def test_DENETLEYICI_surucu_kurallara_UYUYOR():
    from servers.modul_denetleyici import denetle

    assert denetle(KIT / "moduller" / MODUL) == []


def test_MODUL_JSON_gecerli_ve_bekci_EN_AZ_1500():
    from servers.modul_kayit import oku

    m = oku(KIT / "moduller" / MODUL)
    assert m["kimlik"] == MODUL and m["bekci_ms"] >= 1500
