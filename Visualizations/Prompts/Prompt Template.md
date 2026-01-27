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

```
I want to create comprehensive Manim Community Edition visualizations for the mathematical topic: [TOPIC_NAME]

I have attached:
- Homework problems PDF covering this topic
- [Optional: Study guide or textbook sections]

Please create a complete Manim script following these specifications.

### 1. FOUNDATION: The `style_utils.py` Dependency
**Crucial:** The script must import from a local `style_utils.py` file.
You must assume a `BaseScene` class exists that handles the title and grid setup.
Do **not** redefine colors or basic setup in the main script. Use:
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

### DELIVERABLES

Please provide:

1.  **`style_utils.py`**: A robust foundation file defining `BaseScene`, `COLOR_CONSTANTS`, and layout helpers (like `get_standard_grid`).
2.  **Main Python Script** (`[topic_name]_manim.py`): The scenes inheriting from `BaseScene`.
3.  **render.sh**: Quick start script.
4.  **requirements.txt**.

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

Follow the `STYLING_GUIDE.md`:
- **Colors:** Blue/Red for primary vectors. Green for results.
- **Sizes:** Titles 48pt, Formulas 40pt.
- **Layout:** Grid must NOT touch the Title.

---

**End of Template**