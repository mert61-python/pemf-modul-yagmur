# -*- coding: utf-8 -*-
"""Kit test ortamı: kit kökü yolda; modüller kökü `moduller/`; test edilen modül `PEMF_KIT_MODUL` (varsayılan `sablon`)."""

import os
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
os.environ.setdefault("PEMF_MODULLER_KOKU", str(KIT / "moduller"))
os.environ.setdefault("PEMF_KIT_VERI", str(KIT / ".veri"))
MODUL = os.environ.get("PEMF_KIT_MODUL", "sablon")
