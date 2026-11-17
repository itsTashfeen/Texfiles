# Roadmap — MathTex Gemini Automation

Status relative to the original specs (`docs/specs/`) and the Nov 14–16 2026 sessions.

---

## Done (shipped)

- [x] Interactive selection (mouse PDF files/folder + keyboard chapter browse)
- [x] Multi-prompt join with PRIMARY / ADDITIONAL markers
- [x] System instruction picker from `Overleaf/System Instructions/`
- [x] Target subfolder detect / create; prefix-aware `.tex` overwrite (incl. custom folders)
- [x] Models: `gemini-4-argon` (default), `gemini-4-carbon`, `gemini-4-hydrogen`, `gemini-3.1-pro-preview`
- [x] Thinking level high/low; Flex / Batch / Standard / Flex+Batch fallback
- [x] LaTeX fence strip + multi-block stitch + validation + overwrite
- [x] Compile via `watch_tex_to_pdf.py --file`
- [x] Rich summary + Markdown/JSON reports (job-named)
- [x] One-click `Run Automation.bat` / `Run Jobs.bat`
- [x] Named jobs + “Job submitted” confirmation
- [x] Per-PDF request isolation + Strict Section Scope Guard
- [x] InitIn vs BilledIn reporting; Long Decode (1,048,576) for Gemini 4
- [x] Tail-resume for truncated LaTeX
- [x] **Context Cache** for system+prompt (explicit on `gemini-3.1-pro-preview`; graceful skip on Gemini 4)
- [x] **Skip if OK** + **Retry failed sections only** in Run Jobs
- [x] **Pre-submit cost gate** (`count_tokens` + min/likely/max $ + budget confirm)
- [x] **API-only overlap page trim** (on-disk slices unchanged)
- [x] **media_resolution** + smarter thinking defaults by target folder
- [x] **Compile-fix micro-pass** (error log + last ~150 lines)
- [x] Progress ETA, `.tex.bak` backups, `TOKEN_MISMATCH` warning

---

## Open / not built

| Item | Notes |
|------|-------|
| **Prompt/system presets per RelPath** | Remember last model/tier/thinking/folder per chapter |
| **A/B job compare** | Same PDFs, two models; side-by-side cost + compile |
| **Queue / watch folder** | Drop Book PDF slices → overnight Batch enqueue |
| **Live re-verification after isolation** | Full Flex chapter acceptance archived as pass |
| **Billing / credits monitoring** | Operational (Carbon 402) — not a code feature |

---

## Explicit non-goals

- Changing **`Overleaf/.code/slice_pdfs.py`** overlap behavior (trim is API-only)
- Plain-text PDF extraction
- Raising `MAX_WORKERS` until skip/resume + cache are proven in production use
- Editing Cursor plan files under `.cursor/plans/` when implementing

---

## Calibration (Nov 16 2026) — Context Cache on 3.1-pro Flex

Chapter 5.1–5.3 smoke (READY override, no full LaTeX gen):

| Metric | Value |
|--------|-------|
| Cached system+prompt | **3,847** tok/section |
| Cache hits (3 PDFs) | **11,541** total Cache tokens |
| Input-only Flex $ | uncached **$0.0168** → cached **$0.0114** |
| **Input $ drop** | **~32%** on this 3-section calibration |
