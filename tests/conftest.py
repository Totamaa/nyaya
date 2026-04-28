from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_MODULES_DIR = ROOT_DIR / "src" / "app" / "modules"

if str(SRC_MODULES_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_MODULES_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
