# Verification — MathTex Gemini Automation Session

Checklist items and measured results from Nov 14 2026.

---

## A. Path mapping / dry-run

| Check | Result |
|-------|--------|
| Chapter 6 → Homework: `6.3 The Method of Distribution Functions.pdf` | Topic `The Method of Distribution Functions`; target `(Homework) 6.3 The Method of Distribution Functions.tex` |
| Chapter 5 dry-run after Phase E | Sections **5.1**, **5.2**, **5.3** shown in scope mapping table; overwrite Homework targets |
| `latex_processor` manual | `validation_label == 'OK'`; truncated doc → `TRUNCATED_LATEX` |

---

## B. Isolation / scope / media (Phase E unit checks)

| Check | Result |
|-------|--------|
| `MAX_WORKERS` | `1` |
| `PDF_MEDIA_RESOLUTION` | `"medium"` |
| `extract_section_number('5.10 ...')` | `'5.10'` |
| Each of 5.1 / 5.2 / 5.3 | `section_number` matches; scope string contains `Section 5.x` and `STRICT SECTION SCOPE BOUNDARY` |
| `_pdf_part` media | `MEDIA_RESOLUTION_MEDIUM` |
| `build_isolated_user_content` | 1 Content, 2 parts (text + PDF) |
| `Overleaf/.code/slice_pdfs.py` | Untouched (`git status` clean for that path) |
| ReadLints on automation modules | No linter errors |

---

## C. Job-named reports

| Check | Result |
|-------|--------|
| `sanitize_job_filename("Stats Chapter 6.1-6.3")` | `Stats Chapter 6.1-6.3` |
| First write | `Stats Chapter 6.1-6.3.md` / `.json` |
| Collision | `Stats Chapter 6.1-6.3 (YYYYMMDD_HHMMSS).md` / `.json` |
| Forbidden chars | e.g. `Ch5: Sec 5.1/5.2*Test?` → sanitized with `-` |

---

## D. Token accounting helpers

| Check | Result |
|-------|--------|
| Fake meta: `initial_prompt_token_count=5061`, `prompt_token_count=44910` | InitIn=5061, BilledIn=44910 |
| Fake + preflight 5055 without initial | Falls back to preflight when initial missing |
| `summarize_token_diagnostics` | Totals InitIn / BilledIn / Think / Out / cost |

---

## E. Preflight `count_tokens` (after `api_version=v1beta`)

System + scoped prompt + single PDF:

| PDF | argon | 3.1-pro |
|-----|-------|---------|
| 5.1 Introduction.pdf | **4,918** | **4,945** |
| 5.2 Bivariate…pdf | **10,533** | **10,560** |
| 5.3 Marginal…pdf | **11,090** | **11,119** |

Before v1beta fix: preflight printed **0**; `gemini-3.1-pro-preview` returned **404** on API version **v1**.

---

## F. Live runs (pre-isolation accounting; historical)

### `run_20261114_142314.md` — Chapter 5 Homework

| PDF | In | Cache | Think | Out | Cost | LaTeX / Compile | Sec |
|-----|-----|-------|-------|-----|------|-----------------|-----|
| 5.1 | 45,042 | — | 5,624 | 36,153 | $0.2370 | (run report) | 876.6 |
| 5.2 | 69,572 | — | 11,401 | 45,673 | $0.3289 | | 1257.7 |
| 5.3 | 73,696 | — | 17,922 | 47,614 | $0.3737 | **TRUNCATED_LATEX**; compile failed | 1112.2 |
| **Total** | | | | | **$0.9396** | | |

### `run_20261114_154131.md` — Stats Chapter 6.1-6.3

| PDF | In | Think | Out | Cost | Compile |
|-----|-----|-------|-----|------|---------|
| 6.1 | 44,910 | 3,183 | 36,975 | $0.2289 | **Failed** |
| 6.2 | 45,816 | 6,343 | 38,351 | $0.2521 | Compiled |
| 6.3 | 72,130 | 8,658 | 43,695 | $0.3068 | Compiled |
| **Total** | | | | **$0.7878** | |

### `run_20261114_153853.md` — Carbon

**402 RESOURCE_EXHAUSTED** — prepayment credits depleted.

### Wizard showcase sizes (Ch.5)

5.1 **57.7 KB**, 5.2 **122.9 KB**, 5.3 **130.3 KB**.

---

## G. Specs verification (from original attachments)

| Spec item | Session status |
|-----------|----------------|
| Dry-run Ch.6 → Homework 6.3 mapping | **Pass** |
| Live single 6.1 Flex → tex + compile + cost | **Attempted**; at least one run had compile fail |
| Batch-only cancel while PENDING | UI supported; dedicated smoke pass not archived |

---

## H. Jobs observed on disk (session end note)

Example named jobs included Stats Chapter 5 / 6 runs and a **Linear Algebra Chapter 7.2-7.3 Carbon Book Section** entry that could still show `running` in `jobs.json` depending on Batch wait.
