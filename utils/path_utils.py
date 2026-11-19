# -*- coding: utf-8 -*-
"""Kit için yalın veri kökü (ana uygulamada `apps/backend/utils/path_utils.py` — göç / ACL mantığı orada; kitte YOK)."""
import os
from pathlib import Path


def get_app_data_directory() -> str:
    d = Path(os.environ.get("PEMF_KIT_VERI", Path(__file__).resolve().parents[1] / ".veri"))
    d.mkdir(parents=True, exist_ok=True)
    return str(d)
