# -*- coding: utf-8 -*-
"""Arayüz metinleri TR + EN eşliği (ana depodaki K-1 kuralı): `uygulama/src/i18n/tr/*.json` ile `en/*.json` aynı dosyalar ve aynı
anahtarlar. Kullanım: `python araclar/i18n_esle.py` — eşleşmezse çıkış 1. Yeni metin = iki dosyaya da anahtar (KABUL C2)."""

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1] / "uygulama" / "src" / "i18n"


def anahtarlar(d, on=""):
    for k, v in d.items():
        yield from (anahtarlar(v, f"{on}{k}.") if isinstance(v, dict) else [f"{on}{k}"])


def main() -> int:
    tr_dosya = {p.name for p in (KOK / "tr").glob("*.json")}
    en_dosya = {p.name for p in (KOK / "en").glob("*.json")}
    hata = 0
    for ad in sorted(tr_dosya ^ en_dosya):
        print(f"yalnız bir dilde dosya: {ad}")
        hata += 1
    toplam = 0
    for ad in sorted(tr_dosya & en_dosya):
        tr = set(anahtarlar(json.loads((KOK / "tr" / ad).read_text(encoding="utf-8"))))
        en = set(anahtarlar(json.loads((KOK / "en" / ad).read_text(encoding="utf-8"))))
        toplam += len(tr)
        for k in sorted(tr - en):
            print(f"{ad}: EN'de yok: {k}")
        for k in sorted(en - tr):
            print(f"{ad}: TR'de yok: {k}")
        hata += len(tr ^ en)
    print(f"{len(tr_dosya)} dosya · {toplam} anahtar · {hata} uyuşmazlık")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
