# AI Rules & Conventions — MathTex Gemini Automation

Rules for the runner and for future agents working on this project. Derived from the Nov 14 2026 session and implemented code.

---

## 1. Secrets

- Put `GEMINI_API_KEY` in **`MathTex/.env`** only.
- Never leave the real key only in `.env.example` (placeholder: `your_api_key_here`).
- `.env`, `automation/.state/`, and `automation/reports/` are gitignored.

---

## 2. Prompt assembly (`ui_selector.assemble_prompt_text`)

When multiple prompt files are selected (order = join order):

1. First file → `--- PRIMARY INSTRUCTIONS ---` + `# Source: <filename>` + body
2. Further files → `--- ADDITIONAL INSTRUCTIONS ---` + source header + body

Per section, replace `[TOPIC NAME]` with the derived topic from the PDF stem:
- Strip leading section number `^\d+(?:\.\d+)*` (optional dash/colon)
- Strip trailing `(Optional)`
- Collapse whitespace

---

## 3. Strict Section Scope Guard (verbatim structure)

Implemented in `automation/gemini_runner.py` → `build_section_scope_guard()`. Prepended before the user prompt via `build_scoped_prompt()`.

```text
--- STRICT SECTION SCOPE BOUNDARY ---
TARGET SECTION FOR THIS ISOLATED SESSION: Section {sec_num} ({topic})
SOURCE FILE: {pdf_filename}
CRITICAL BOUNDARY RULES:
1. This is a completely standalone, single-PDF session. Cover ONLY the theory, examples,
   and exercises that belong to {target_label}.
2. The first page and/or final page of the attached PDF intentionally includes up to 1 page
   of boundary overlap from the immediately preceding or following textbook section so no
   sentence or formula is cut off.
3. IGNORE any exercises or text on page 1 that belong to the END of the preceding section,
   and STOP immediately when the next section's heading begins on the final overlap page.
4. NEVER recall, reconstruct, or continue into exercises from earlier or later sections
   from your pretraining memory—solve ONLY what belongs to this target section as printed in
   the attached PDF.
--- END OF SCOPE BOUNDARY ---
```

If no section number is extracted, target label falls back to `Topic '{topic}' ({stem})`.

---

## 4. Request isolation (hard rules)

1. **One PDF per generation call** — never attach multiple section PDFs to one `contents` payload.
2. **Fresh `genai.Client` per PDF** (and per retry attempt) — no shared HTTP/session/continuation state.
3. **`api_version="v1beta"`** on the client HttpOptions.
4. **Default `MAX_WORKERS = 1`** — sequential `[1/N]`, `[2/N]`, …
5. Build `types.Content(role="user", parts=[text_part, pdf_part])` and **assert exactly one media/PDF part**.
6. Log isolation line with pages, size, sha256, media resolution, preflight tokens.

---

## 5. PDF media resolution

- Always set `media_resolution` on the PDF `Part` (config: `PDF_MEDIA_RESOLUTION`, default `"medium"` → 560 tokens/page).
- Allowed: `"low"` | `"medium"` | `"high"`.
- Do not strip PDFs to plain text for token savings.

---

## 6. Token reporting semantics

| Column | Meaning | Source |
|--------|---------|--------|
| **InitIn** | Single-turn System + scoped prompt + one PDF (AI Studio–like) | `initial_prompt_token_count` or preflight |
| **BilledIn** | Cumulative input across continuation hops | `prompt_token_count` |
| Cost USD | Billable input − cached + (output + thinking) × rates | Uses **BilledIn** |

Always show both InitIn and BilledIn in Rich tables and Markdown/JSON reports. Store `token_diagnostics` on named jobs in `jobs.json`.

---

## 7. LaTeX validation labels

| Label | Meaning |
|-------|---------|
| `OK` | Has `\documentclass` and `\end{document}` |
| `TRUNCATED_LATEX` | Missing end document / truncated |
| `MISSING_DOCUMENTCLASS` | No `\documentclass` |

Strip Markdown fences (```` ```latex ```` / ```` ``` ````) before write. UTF-8 overwrite of target `.tex`.

---

## 8. Compiler hook

Prefer `Overleaf/watch_tex_to_pdf.py --file <tex>` (SUBST short paths + mirrored PDF). Do not replace with full-tree `convert_tex_to_pdf.py` for per-section runs.

Success = mirrored `.pdf` exists and size > 0.

---

## 9. Do-not-touch / out of scope for agents

Unless the user **explicitly** asks:

- Do **not** edit `Overleaf/.code/slice_pdfs.py` (1-page overlap is intentional).
- Do **not** edit `Overleaf/.code/mirror_pdf_tree.py` as part of the runner.
- Do **not** invent or overwrite System Instruction content in `Overleaf/System Instructions/`.
- Do **not** integrate Overleaf cloud sync (`olsync`).
- Do **not** switch PDF input to text-only extraction.

---

## 10. Job naming & reports

- Require a job name before interactive submit; print “Job submitted” confirmation.
- Report files: `automation/reports/<Job Name>.md` and `.json` (Windows-safe sanitize; timestamp suffix only on name collision).
- Include Job Name and Job ID in report headers / JSON root.
- Jobs manager (`Run Jobs.bat`) must show full settings snapshot (PDFs, prompts, system, model, thinking, tier, mapping, Batch IDs, token diagnostics).

---

## 11. Retry policy

- Retry on 429 / 503 / timeout / capacity-style errors with Flex backoff 15→45→90s.
- Do **not** blindly retry **402** / prepayment credits depleted.
- Flex + Auto Batch Fallback: after Flex exhaustion, submit Batch and offer Wait / Cancel / Exit.

---

## 12. Output token ceilings (Long Decode)

- Gemini 4 (`argon`, `carbon`, `hydrogen`): request **`max_output_tokens=1_048_576`** via `max_output_tokens_for_model()`.
- `gemini-3.1-pro-preview`: keep **65_536**; rely on `automatic_continuation` + up to `MAX_LATEX_CONTINUATION_TURNS` (2) tail-resume if `\end{document}` missing.
- Always set `automatic_continuation=True` on sync/flex `generate_content` (omit on Batch inline configs).
- Never mark `success=True` when LaTeX is `TRUNCATED_LATEX` / `MISSING_DOCUMENTCLASS` or compile failed.

## 13. LaTeX extraction

- Prefer `extract_latex_source()` / `process_latex_response()` over naive single-fence strip.
- Prefer `extract_response_text_and_meta()` over bare `response.text` for finish_reason diagnostics.

## 14. Jobs UI

- Default list = current (`submitted`/`running`) only.
- History via Succeeded / Failed (failed+partial+cancelled) / All / By Model.
- Use `effective_job_status()` when filtering so historical truncated runs appear under Failed.

## 15. GitHub pushes of this repo

- Never push multi-GB packs in one shot; use ≤350 MB sequential chunk commits when PDFs are included.
