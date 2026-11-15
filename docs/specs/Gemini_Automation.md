# MathTex Gemini Automation & PDF Compilation Roadmap

## 1. Objective & End-to-End Workflow
Automate the generation of rigorous LaTeX study guides, homework solutions, and 30-problem practice sets from chapter PDFs using the Google GenAI Python SDK (`google-genai`), overwriting target `.tex` files in the mirrored Overleaf directory tree, compiling them into final PDFs via the existing compiler script, and producing a full token, cost, and compilation report.

### End-to-End Pipeline
1. **Interactive Selection (Mouse GUI or Keyboard TUI):**
   - Pick a source `Book PDF` directory (full chapter) or select specific section `.pdf` files.
   - Pick 1 or more prompt `.txt` files from `Overleaf\Prompts\`.
   - Pick 1 system instruction file from `Overleaf\System Instructions\`.
   - Pick the target `.tex` subfolder (`Homework`, `Problem Sets`, `Book Section`, or custom).
   - Pick the model (`gemini-4-argon`, `gemini-4-carbon`, `gemini-3.1-pro-preview`) and execution tier (`Flex -> Batch Fallback`, `Flex Only`, `Batch Only`, `Standard`).
2. **Dynamic Prompt Assembly & Topic Derivation:**
   - Auto-derive `[TOPIC NAME]` from each PDF filename.
   - Concatenate multiple selected prompt files cleanly with section delimiters.
3. **Resilient API Execution (`Flex` with Automatic `Batch` Fallback):**
   - Run concurrent `service_tier="flex"` requests (50% discount) with exponential backoff on `429`/`503` capacity errors and 15-minute timeouts.
   - Automatically bundle any sections that exhaust Flex retries into an asynchronous `Batch` job (also 50% discount), persisting job metadata locally so it can be polled, resumed, or canceled (`client.batches.cancel`) at any time.
4. **LaTeX Sanitization & Overwrite:**
   - Strip Markdown fences (` ```latex `), validate `\documentclass` ... `\end{document}`, and overwrite the matching prefixed `.tex` file (e.g., `(Homework) 6.3 The Method of Distribution Functions.tex`).
5. **Auto-Compilation & Final Audit Report:**
   - Invoke the existing `.tex -> .pdf` compiler script on all updated `.tex` files so compiled PDFs land in the mirrored `.pdf` subfolder.
   - Display a terminal summary table and write a persistent Markdown + JSON run report.

---

## 2. Directory Mapping & Filename Conventions

### Base Paths
- **Repository Root:** `D:\Users\Tashfeen Omran\Documents\Not Synced\GitHub\MathTex`
- **Overleaf Root:** `...\MathTex\Overleaf`
- **PDF Tree Root:** `...\Overleaf\.pdf`
- **TeX Tree Root:** `...\Overleaf\.tex`
- **Prompts Directory:** `...\Overleaf\Prompts`
- **System Instructions Directory:** `...\Overleaf\System Instructions` *(new dedicated folder for AI Studio system instruction `.txt`/`.md` files)*

### Path & Prefix Resolution Rules
Given a selected source PDF:
`...\Overleaf\.pdf\<Domain>\<Subject>\<Chapter>\Book PDF\<Filename>.pdf`

1. **Relative Course Path Extraction:**
   - Extract `<RelPath>` = `<Domain>\<Subject>\<Chapter>` (e.g., `ML\Statistics & Probability\Chapter 6 - Functions of Random Variables`).
2. **Target `.tex` Directory:**
   - `...\Overleaf\.tex\<RelPath>\<TargetSubfolder>\` (e.g., `...\Homework\`, `...\Problem Sets\`, `...\Book Section\`).
3. **Target `.tex` Filename Resolution (Smart Prefix Matching):**
   - **Step A (Existing Placeholder Match):** Scan `<TargetDir>` for an existing `.tex` file matching `*<Filename>.tex` (for example, `(Homework) 6.3 The Method of Distribution Functions.tex`). If found, overwrite that exact file.
   - **Step B (New File Fallback Prefix):** If no placeholder exists yet, apply the folder-to-prefix map:
     - `Homework` -> `(Homework) <Filename>.tex`
     - `Problem Sets` -> `(Problem Set) <Filename>.tex`
     - `Book Section` -> `(Book Section) <Filename>.tex`
     - Any other folder `<Folder>` -> `(<Folder>) <Filename>.tex`
4. **Topic Name Auto-Derivation (`[TOPIC NAME]`):**
   - Strip `.pdf` extension.
   - Strip leading chapter/section numbers via regex: `^\d+(?:\.\d+)*\s*[-–:]?\s*`.
   - Strip trailing `(Optional)` tag if present.
   - *Example:* `6.6 Multivariable Transformations Using Jacobians (Optional).pdf` -> `Multivariable Transformations Using Jacobians`.
   - Replace every `[TOPIC NAME]` token across all selected prompt templates.

---

## 3. Project File Structure

```text
D:\Users\Tashfeen Omran\Documents\Not Synced\GitHub\MathTex\
├── automation/
│   ├── main.py                  # CLI entry point & interactive workflow orchestrator
│   ├── config.py                # Paths, model pricing table, prefix rules, concurrency defaults
│   ├── ui_selector.py           # Hybrid Mouse (Tkinter file dialog) & Keyboard (Questionary) picker
│   ├── path_mapper.py           # .pdf <-> .tex path translation, prefix matching & topic extractor
│   ├── gemini_runner.py         # Flex concurrent runner, retry logic, Batch fallback & Batch cancel/poll
│   ├── latex_processor.py       # Fence stripping, structural validation & safe .tex file overwrite
│   ├── pdf_compiler_hook.py     # Subprocess wrapper calling existing .tex -> .pdf compiler script
│   ├── reporter.py              # Token/cost calculator, Rich terminal summary & Markdown/JSON report
│   ├── .state/
│   │   └── batch_jobs.json      # Persistent registry of pending/running Batch jobs for resume/cancel
│   └── reports/
│       └── run_YYYYMMDD_HHMMSS.md
├── Overleaf/
│   ├── Prompts/                 # Existing prompt .txt files
│   ├── System Instructions/     # Drop AI Studio system instruction .txt/.md files here
│   ├── .pdf/
│   └── .tex/
└── roadmap.md