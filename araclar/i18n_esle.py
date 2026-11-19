# -*- coding: utf-8 -*-
"""Panel metinleri TR + EN anahtar eşliği (ana depodaki K-1 kuralı): `python araclar/i18n_esle.py` — eşleşmezse çıkış 1."""

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1] / "arayuz" / "i18n"


def anahtarlar(d, on=""):
    for k, v in d.items():
        yield from (anahtarlar(v, f"{on}{k}.") if isinstance(v, dict) else [f"{on}{k}"])


def main() -> int:
    tr = set(anahtarlar(json.loads((KOK / "tr.json").read_text(encoding="utf-8"))))
    en = set(anahtarlar(json.loads((KOK / "en.json").read_text(encoding="utf-8"))))
    for k in sorted(tr - en):
        print(f"EN'de yok: {k}")
    for k in sorted(en - tr):
        print(f"TR'de yok: {k}")
    print(f"{len(tr)} TR · {len(en)} EN anahtar")
    return 0 if tr == en else 1


if __name__ == "__main__":
    sys.exit(main())
