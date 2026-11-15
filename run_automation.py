#!/usr/bin/env python3
"""One-shot launcher: interactive PDF → Gemini → .tex → PDF pipeline.

Double-click ``Run Automation.bat`` or run::

    python run_automation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.main import main


if __name__ == "__main__":
    # No CLI flags → full interactive chooser (PDFs, prompts, system
    # instructions, target folder, model, thinking, tier).
    raise SystemExit(main([]))
