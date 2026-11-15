#!/usr/bin/env python3
"""One-shot launcher: inspect / cancel / resume named automation jobs.

Double-click ``Run Jobs.bat`` or run::

    python run_jobs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.main import main


if __name__ == "__main__":
    raise SystemExit(main(["--jobs"]))
