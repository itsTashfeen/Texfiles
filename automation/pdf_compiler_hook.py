"""Subprocess wrapper around Overleaf/watch_tex_to_pdf.py --file."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import EXISTING_COMPILER_SCRIPT
from .path_mapper import mirrored_pdf_for_tex


@dataclass
class CompileResult:
    tex_path: Path
    pdf_path: Path
    success: bool
    returncode: int
    stdout: str
    stderr: str
    error_lines: list[str]

    @property
    def status_label(self) -> str:
        if self.success:
            return f"Compiled ({self.pdf_path})"
        detail = "; ".join(self.error_lines[:3]) if self.error_lines else "Failed"
        return f"Failed: {detail}"


def _extract_error_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        if line.startswith("!") or "LaTeX Error" in line or "Undefined control sequence" in line:
            lines.append(line.strip())
    return lines


def compile_tex(tex_path: Path, *, timeout: int = 300) -> CompileResult:
    tex_path = Path(tex_path).resolve()
    pdf_path = mirrored_pdf_for_tex(tex_path)
    script = EXISTING_COMPILER_SCRIPT.resolve()

    if not script.is_file():
        return CompileResult(
            tex_path=tex_path,
            pdf_path=pdf_path,
            success=False,
            returncode=-1,
            stdout="",
            stderr=f"Compiler script not found: {script}",
            error_lines=[f"Compiler script not found: {script}"],
        )

    proc = subprocess.run(
        [sys.executable, str(script), "--file", str(tex_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=str(script.parent),
    )
    combined = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    error_lines = _extract_error_lines(combined)
    success = (
        proc.returncode == 0
        and pdf_path.is_file()
        and pdf_path.stat().st_size > 0
    )
    if not success and pdf_path.is_file() and pdf_path.stat().st_size > 0:
        # watch_tex_to_pdf may exit 0 even with warnings; size check is authoritative.
        success = True

    return CompileResult(
        tex_path=tex_path,
        pdf_path=pdf_path,
        success=success,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        error_lines=error_lines,
    )


def compile_many(tex_paths: list[Path]) -> list[CompileResult]:
    return [compile_tex(path) for path in tex_paths]
