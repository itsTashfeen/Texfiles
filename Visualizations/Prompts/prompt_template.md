```markdown
# MANIM VISUALIZATION GENERATION PROMPT
## Template for Creating Comprehensive Mathematical Visualizations

---

## INSTRUCTIONS FOR USE

1. Replace `[TOPIC_NAME]` with your specific topic.
2. Provide your homework PDF/Problem Set.
3. Run the prompt.

---

## PROMPT TEMPLATE

```text
I want to create comprehensive Manim Community Edition visualizations for the mathematical topic: [TOPIC_NAME]

I have attached:
- Homework problems PDF covering this topic
- [Optional: Study guide or textbook sections]

Please create a complete Manim script following these specifications.

### 1. FOUNDATION: The `style_utils.py` Dependency
**Crucial:** I am working in a Jupyter Notebook.
The script must import from a local `style_utils.py` file.
You must assume a `BaseScene` class exists that handles the title and grid setup.
Do **not** redefine colors or basic setup in the notebook cells. Use:
```python
from manim import *
from style_utils import *
```

### 2. LAYOUT & POSITIONING RULES (Non-Negotiable)
To prevent misalignment (e.g., arrows overlapping titles):
1.  **Respect Safe Zones:**
    *   **Title Zone:** Top 15% (Y > 3.0). No grid or vectors here.
    *   **Content Zone:** Middle 60% (Y between -2.5 and 3.0).
    *   **Footer Zone:** Bottom 25% (Y < -2.5). Calculations/Formulas here.
2.  **Grid Setup:** Use `self.get_standard_grid()` from `BaseScene`. Do not manually create large NumberPlanes that hit the top edge.
3.  **Dynamic Boxing:** Never use fixed-size Rectangles for formulas.
    *   Create the `MathTex` content first.
    *   Group it: `content = VGroup(...)`
    *   Wrap it: `box = SurroundingRectangle(content, color=..., fill_opacity=0.9)`
    *   This ensures formulas never spill out of their background.

### 3. CONTENT REQUIREMENTS

**Progressive Scene Structure:**
*   Scene 1: Introduction (Definitions & Intuition)
*   Scene 2-3: Basic Computation (Algebraic)
*   Scene 4-5: Geometric Visualization (The "Why")
*   Scene 6-7: Advanced Concepts/Applications
*   Scene 8: Real-World Application (Finance/Physics)
*   Scene 9: Summary

**Educational Approach:**
*   **Dual Coding:** Show the Algebra (left/bottom) and Geometry (center/right) simultaneously.
*   **Step-by-Step:** Don't just show the answer. Animate the substitution.

### 4. VISUALIZATION REQUIREMENTS

*   **Color Consistency:** Use `COLOR_VECTOR_A` (Blue) and `COLOR_VECTOR_B` (Red) strictly.
*   **Readability:** All text over grids must have a `BackgroundRectangle` or be inside a container.
*   **Pacing:** Use `self.wait(2)` after major steps. No "rushed" animations.

### DELIVERABLES (JUPYTER NOTEBOOK FORMAT)

Please provide the output as **separate Python code blocks** corresponding to Jupyter Notebook cells.

**Block 1: Imports**
*   Standard imports and the `style_utils` import.

**Block 2 - Block 10: Individual Scenes**
*   Each scene must be in its own code block.
*   **CRITICAL:** Prepend the block with the specific magic command to run it.
    *   Example: `%%manim -qm -v WARNING Scene01_Introduction`
*   Do not put multiple scenes in one block.

### SCENE PACING TEMPLATE

```
[0-5s]    Title (Handled by BaseScene)
[5-10s]   Subtitle/Context
[10-40s]  Main Visualization (in Content Zone)
[40-60s]  Calculation overlay (in Footer Zone)
[60-70s]  Summary/Pause
```

### EXAMPLES TO INCLUDE

Please visualize these aspects of [TOPIC_NAME]:
1. [Specific concept 1]
2. [Specific concept 2]
3. [Specific example from homework]
4. [Common mistake or pitfall]

---

## STYLE CONSISTENCY

Follow the `styling_guide.md`:
- **Colors:** Blue/Red for primary vectors. Green for results.
- **Sizes:** Titles 48pt, Formulas 40pt.
- **Layout:** Grid must NOT touch the Title.

---

**End of Template**
```

### How to use this now:

1.  **Context:** Paste `PROMPT_TEMPLATE.md` (the version above) and `STYLING_GUIDE.md` into Claude/ChatGPT.
2.  **Request:** "Generate the Manim scripts for [Topic]."
3.  **Result:** The AI will give you:
    *   **Code Block 1:** Imports (Copy to Cell 1).
    *   **Code Block 2:** `%%manim ... Scene 1` (Copy to Cell 2).
    *   **Code Block 3:** `%%manim ... Scene 2` (Copy to Cell 3).

This is the most efficient workflow for PyCharm + Jupyter.