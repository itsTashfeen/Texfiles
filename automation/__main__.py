"""Allow `python -m automation` as well as `python -m automation.main`."""

from .main import main

raise SystemExit(main())
