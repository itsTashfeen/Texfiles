"""
Two-way sync helper for the Overleaf "Courses" project.

Uses the local .olauth cookie and the patched overleaf-sync client.

Usage:
  python sync_courses.py              # two-way sync
  python sync_courses.py --pull       # remote -> local only
  python sync_courses.py --push       # local -> remote only
  python sync_courses.py --clean-remote  # delete .olignore'd files from Overleaf (asks once)
  python sync_courses.py --watch      # pull every N seconds + watch .tex->.pdf
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_NAME = "Courses"
COOKIE = ROOT / ".olauth"
WATCH_SCRIPT = ROOT / "watch_tex_to_pdf.py"


def ols_command() -> list[str]:
    # Run the patched client vendored in ./olsync, not the pip-installed one.
    return [sys.executable, "-m", "olsync.olsync"]


def run_ols(mode: str | None = None) -> int:
    if not COOKIE.exists():
        print(f"Missing {COOKIE}. Run `ols login` in this folder first.")
        return 1

    cmd = [*ols_command(), "-n", PROJECT_NAME, "--store-path", str(COOKIE)]
    if mode == "pull":
        cmd.append("-r")
    elif mode == "push":
        cmd.append("-l")
    elif mode == "clean":
        cmd.append("--clean-remote")

    # Ignore local-only artifacts so they are never pushed to Overleaf.
    olignore = ROOT / ".olignore"
    if olignore.exists():
        cmd.extend(["-i", str(olignore)])

    print("Running:", " ".join(cmd))
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.call(cmd, cwd=str(ROOT), env=env)


def watch_loop(sync_every: int, mode: str) -> int:
    print(f"Starting daemon: sync every {sync_every}s ({mode}), watching .tex -> .pdf")
    print("Press Ctrl+C to stop.\n")

    watcher = subprocess.Popen(
        [sys.executable, str(WATCH_SCRIPT), "--poll", "2"],
        cwd=str(ROOT),
    )
    try:
        while True:
            code = run_ols(None if mode == "two-way" else mode)
            if code != 0:
                print(f"Sync exited with code {code}; will retry after interval.")
            time.sleep(sync_every)
    except KeyboardInterrupt:
        print("\nStopping daemon...")
    finally:
        watcher.terminate()
        try:
            watcher.wait(timeout=5)
        except subprocess.TimeoutExpired:
            watcher.kill()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Overleaf Courses project.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pull", action="store_true", help="Remote -> local only")
    group.add_argument("--push", action="store_true", help="Local -> remote only")
    group.add_argument(
        "--clean-remote",
        action="store_true",
        help="Delete files matching .olignore from Overleaf (lists them, asks once)",
    )
    group.add_argument(
        "--watch",
        action="store_true",
        help="Keep syncing on an interval and watch .tex for PDF conversion",
    )
    parser.add_argument(
        "--every",
        type=int,
        default=90,
        help="With --watch, sync interval in seconds (default: 90)",
    )
    parser.add_argument(
        "--watch-mode",
        choices=["two-way", "pull", "push"],
        default="two-way",
        help="Sync direction used by --watch (default: two-way)",
    )
    args = parser.parse_args()

    os.chdir(ROOT)

    if args.watch:
        return watch_loop(args.every, args.watch_mode)

    if args.pull:
        return run_ols("pull")
    if args.push:
        return run_ols("push")
    if args.clean_remote:
        return run_ols("clean")
    return run_ols(None)


if __name__ == "__main__":
    sys.exit(main())
