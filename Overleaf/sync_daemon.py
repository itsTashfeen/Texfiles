"""
Background two-way Overleaf sync daemon for the Courses project.
Logs to sync_daemon.log. Intended to run hidden via start_sync_daemon.ps1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_NAME = "Courses"
COOKIE = ROOT / ".olauth"
OLIGNORE = ROOT / ".olignore"
LOG_FILE = ROOT / "sync_daemon.log"
PID_FILE = ROOT / "sync_daemon.pid"
WATCH_SCRIPT = ROOT / "watch_tex_to_pdf.py"
INTERVAL_SECONDS = 60


def log(message: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {message}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def write_pid() -> None:
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def clear_pid() -> None:
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except OSError:
        pass


def ols_command() -> list[str]:
    # Run the patched client vendored in ./olsync, not the pip-installed one.
    return [sys.executable, "-m", "olsync.olsync"]


def run_two_way_sync() -> int:
    if not COOKIE.exists():
        log(f"ERROR: missing cookie file {COOKIE}")
        return 1

    cmd = [
        *ols_command(),
        "-n",
        PROJECT_NAME,
        "--store-path",
        str(COOKIE),
    ]
    if OLIGNORE.exists():
        cmd.extend(["-i", str(OLIGNORE)])

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    # Non-interactive answers for rare prompts:
    # - 'n' = do not overwrite a newer file with an older one
    # - 'i' = ignore deleted-file prompts if they appear
    auto_answers = ("n\n" + "i\n") * 500

    log("Starting two-way sync...")
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        input=auto_answers,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(result.stdout)
            if not result.stdout.endswith("\n"):
                f.write("\n")
    if result.stderr:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(result.stderr)
            if not result.stderr.endswith("\n"):
                f.write("\n")

    if result.returncode == 0:
        log("Sync finished OK")
    else:
        log(f"Sync finished with exit code {result.returncode}")
    return result.returncode


def prune_orphan_pdfs() -> int:
    cmd = [sys.executable, str(WATCH_SCRIPT), "--prune"]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(result.stdout)
            if not result.stdout.endswith("\n"):
                f.write("\n")
    if result.stderr:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(result.stderr)
            if not result.stderr.endswith("\n"):
                f.write("\n")
    if result.returncode == 0:
        log("PDF prune finished")
    else:
        log(f"PDF prune exited with {result.returncode}")
    return result.returncode


def main() -> int:
    os.chdir(ROOT)
    write_pid()
    log(f"Daemon started (pid={os.getpid()}, every {INTERVAL_SECONDS}s)")
    try:
        while True:
            try:
                run_two_way_sync()
                prune_orphan_pdfs()
            except Exception as exc:
                log(f"ERROR during sync: {exc!r}")
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        log("Daemon stopped by KeyboardInterrupt")
    finally:
        clear_pid()
        log("Daemon exited")
    return 0


if __name__ == "__main__":
    sys.exit(main())
