# Roadmap — MathTex Gemini Automation

Status relative to the original specs (`docs/specs/`) and the Nov 14 2026 session.

---

## Done (shipped this session)

- [x] Interactive selection (mouse PDF files/folder + keyboard chapter browse)
- [x] Multi-prompt join with PRIMARY / ADDITIONAL markers
- [x] System instruction picker from `Overleaf/System Instructions/`
- [x] Target subfolder detect / create; prefix-aware `.tex` overwrite
- [x] Models: `gemini-4-argon` (default), `gemini-4-carbon`, `gemini-3.1-pro-preview`
- [x] Thinking level high/low; Flex / Batch / Standard / Flex+Batch fallback
- [x] LaTeX fence strip + validation + overwrite
- [x] Compile via `watch_tex_to_pdf.py --file`
- [x] Rich summary + Markdown/JSON reports
- [x] One-click `Run Automation.bat` / `run_automation.py`
- [x] Selected PDF showcase table (name, relative path, size)
- [x] `.env` / `.env.example` key recovery
- [x] Named jobs + “Job submitted” confirmation
- [x] `Run Jobs.bat` / `run_jobs.py` — list, inspect full settings, cancel, wait Batch
- [x] Per-PDF request isolation (fresh Client, `MAX_WORKERS=1`, single PDF Content)
- [x] Strict Section Scope Guard (preserve 1-page slice overlap)
- [x] `media_resolution=MEDIUM`; preflight `count_tokens`; `api_version=v1beta`
- [x] InitIn vs BilledIn reporting; cost from billed
- [x] Job-named report files + `token_diagnostics` in `jobs.json`
- [x] Docs archive (`docs/`) from this chat

---

## Open / not built (mentioned in chat or intermediate plans)

| Item | Notes |
|------|-------|
| **`TOKEN_MISMATCH` flag** | Intermediate plan idea: flag when API billed/initial input ≫ preflight (e.g. >2×). Not in final code. |
| **Live re-verification after isolation** | Preflight + dry-run verified; full live Flex run after Phase E not completed in-session as acceptance of leakage fix. |
| **Long-section truncation handling** | 5.3 hit `TRUNCATED_LATEX` / high Out (~47k). Possible follow-ups: continuation UX, split prompts, or post-process recovery. |
| **Compile failure triage** | 6.1 compile Failed in `run_20261114_154131` — content/compiler debugging still open. |
| **Billing / credits monitoring** | Carbon run hit 402 prepayment depleted — operational, not a code feature. |
| **Batch cancel smoke test** | Specs asked for batch-only 1-file → Cancel while PENDING; not fully documented as passed in transcript. |

---

## Specs checklist (from original attachments)

From `Gemini_Automation.md` / Detailed Module Specs — verification intent:

1. `--dry-run` Chapter 6 → Homework mapping for 6.3 — **done**
2. Live single PDF (6.1) Flex → tex + compile + cost — **attempted** (compile fail on one Ch.6 run)
3. Batch-only cancel while pending — **partially wired** in UI; smoke result not archived as pass

---

## Out of scope (explicit)

- Changing **`Overleaf/.code/slice_pdfs.py`** to remove 1-page boundary overlap
- Changing **`mirror_pdf_tree.py`** as part of the automation runner
- Building/shipping System Instruction **content**
- Overleaf cloud sync (**`olsync`**)
- Switching PDF input to **plain-text extraction** for cheaper tokens
- Editing Cursor plan files under `.cursor/plans/` when implementing (user instruction)

---

## Suggested next priorities (derived, not committed)

1. Live run Chapters 5.1–5.3 after isolation; confirm no adjacent-section exercises and InitIn ≈ preflight.
2. Decide truncation strategy for long Homework generations.
3. Optionally add `TOKEN_MISMATCH` warning when BilledIn/InitIn ratio is extreme (still bill from BilledIn).
4. Fix or document 6.1-style compile failures.
