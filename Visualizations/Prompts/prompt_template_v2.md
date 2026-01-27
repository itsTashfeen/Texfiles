# MANIM VISUALIZATION GENERATION PROMPT
## Template for Creating Comprehensive Mathematical Visualizations
**Version 2.0 - Updated January 2026**

---

## INSTRUCTIONS FOR USE

1. Replace `[TOPIC_NAME]` with your specific topic.
2. Replace `[PROJECT_NAME]` with your project folder name (e.g., `dot_product`, `cross_product`).
3. Provide your homework PDF/Problem Set.
4. Run the prompt.

---

## PROMPT TEMPLATE

```text
I want to create comprehensive Manim Community Edition visualizations for the mathematical topic: [TOPIC_NAME]

Project Name: [PROJECT_NAME]

I have attached:
- Homework problems PDF covering this topic
- style_utils.py (my base styling file)
- common_issues.md (known problems to avoid)
- [Optional: Study guide or textbook sections]

Please create a complete Manim script following these specifications.

### 1. FOUNDATION: Project Setup & Dependencies

**Working Directory:**
```
C:\Users\Computer\Documents\GitHub\MathTex\Visualizations\
```

**Output Directory:**
```
C:\Users\Computer\Documents\GitHub\MathTex\Visualizations\media\videos\[PROJECT_NAME]\720p30\
```

**Dependencies:**
- I already have `style_utils.py` in my working directory
- It contains `BaseScene` class with title/grid setup
- Review it and tell me if any project-specific additions are needed
- Do NOT redefine colors or basic setup

**Required Cell 1 Setup:**
```python
import sys
import os

BASE_DIR = r'C:\Users\Computer\Documents\GitHub\MathTex\Visualizations'
sys.path.append(BASE_DIR)
os.chdir(BASE_DIR)
os.environ['MANIM_OUTPUT_DIR'] = os.path.join(BASE_DIR, 'media')

from manim import *
from style_utils import *
import numpy as np

config.output_file = "[PROJECT_NAME]"

print(f"Working directory: {os.getcwd()}")
print(f"Output will go to: media/videos/[PROJECT_NAME]/")
```

### 2. LAYOUT & POSITIONING RULES (Non-Negotiable)

**Respect Safe Zones:**
- **Title Zone:** Top (Y > 3.0). No grid or vectors here.
- **Content Zone:** Middle (Y between -2.5 and 3.0). Main visualizations.
- **Footer Zone:** Bottom (Y < -2.5). Calculations/Formulas.

**Grid Setup:** 
- Use `self.get_standard_grid()` from `BaseScene`
- Do not manually create large NumberPlanes that hit the top edge

**Dynamic Boxing:** 
- Never use fixed-size Rectangles for formulas
- Create content first, then wrap: `SurroundingRectangle(content, ...)`

### 3. CONTENT REQUIREMENTS

**Progressive Scene Structure:**
- Scene 1: Introduction (Definitions & Intuition)
- Scene 2-3: Basic Computation (Algebraic)
- Scene 4-5: Geometric Visualization (The "Why")
- Scene 6-7: Advanced Concepts/Applications
- Scene 8: Real-World Application (Finance/Physics)
- Scene 9: Summary

**Educational Approach:**
- **Dual Coding:** Show Algebra and Geometry simultaneously
- **Step-by-Step:** Animate substitutions, don't just show answers
- **Pacing:** Use `self.wait(PAUSE_MEDIUM)` after major steps

### 4. VISUALIZATION REQUIREMENTS

- **Color Consistency:** Use `COLOR_VECTOR_A` (Blue), `COLOR_VECTOR_B` (Red), `COLOR_RESULT` (Green)
- **Readability:** All text over grids must have `BackgroundRectangle`
- **Professional Quality:** Follow all sizing standards from `style_utils.py`

---

## DELIVERABLES (CONSOLIDATED FORMAT)

### Block 1: Setup Cell
Provide Cell 1 with all imports and configuration (see above).

### Block 2: ALL SCENES IN ONE BLOCK
Provide ALL scene classes (Scene01 through Scene09) in a SINGLE code block.
- Include complete class definitions for all scenes
- User will copy-paste once into a Jupyter cell
- User will run individual scenes from another cell using magic commands

Example structure:
```python
# ALL SCENES - Copy this entire block into one Jupyter cell

class Scene01_Introduction(BaseScene):
    def __init__(self, **kwargs):
        super().__init__(title="...", **kwargs)
    def construct(self):
        # Scene 1 code

class Scene02_BasicComputation(BaseScene):
    def __init__(self, **kwargs):
        super().__init__(title="...", **kwargs)
    def construct(self):
        # Scene 2 code

# ... (all remaining scenes)
```

### Block 3: Individual Scene Runner Cell
Provide a cell with magic commands to run specific scenes:
```python
# CHOOSE WHICH SCENE TO RENDER:
# Uncomment ONE line below and run this cell

# %%manim -qm -v WARNING Scene01_Introduction
# %%manim -qm -v WARNING Scene02_BasicComputation
# %%manim -qm -v WARNING Scene03_ThreeDimensional
# %%manim -qm -v WARNING Scene04_GeometricVisualization
# %%manim -qm -v WARNING Scene05_FindingAngles
# %%manim -qm -v WARNING Scene06_Orthogonality
# %%manim -qm -v WARNING Scene07_Projections
# %%manim -qm -v WARNING Scene08_RealWorldApplication
# %%manim -qm -v WARNING Scene09_Summary
```

### Block 4: FFmpeg Video Concatenation
Provide a complete FFmpeg concatenation script:
```python
import subprocess
import os

# Configuration
video_dir = r"C:\Users\Computer\Documents\GitHub\MathTex\Visualizations\media\videos\[PROJECT_NAME]\720p30"
project_name = "[PROJECT_NAME]"

# List all scene videos in order
scenes = [
    "Scene01_Introduction.mp4",
    "Scene02_BasicComputation.mp4",
    # ... (all scenes)
]

# Create concat file
concat_file = os.path.join(video_dir, "concat_list.txt")
with open(concat_file, "w") as f:
    for scene in scenes:
        filepath = os.path.join(video_dir, scene)
        if os.path.exists(filepath):
            f.write(f"file '{scene}'\n")
            print(f"✓ Added: {scene}")
        else:
            print(f"✗ Missing: {scene}")

# Run FFmpeg
output_path = os.path.join(video_dir, f"{project_name}_Complete.mp4")
cmd = [
    "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file,
    "-c", "copy", output_path
]

try:
    subprocess.run(cmd, check=True, cwd=video_dir)
    print(f"\n✅ Complete video saved to: {output_path}")
except FileNotFoundError:
    print("\n❌ FFmpeg not found. Install FFmpeg or use a video editor.")
except subprocess.CalledProcessError as e:
    print(f"\n❌ Error: {e}")
```

---

## SCENE PACING TEMPLATE

```
[0-5s]    Title (Handled by BaseScene)
[5-10s]   Subtitle/Context
[10-40s]  Main Visualization (in Content Zone)
[40-60s]  Calculation overlay (in Footer Zone)
[60-70s]  Summary/Pause
```

---

## EXAMPLES TO INCLUDE

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

## IMPORTANT REMINDERS

1. **Review common_issues.md** - Do not repeat known errors
2. **Check style_utils.py** - Tell me if project-specific additions are needed
3. **Consolidated Output** - All scenes in ONE block for easy copy-paste
4. **Quality Flag** - Use `-qm` (720p30) for development, `-qh` for final export

---

**End of Template**
```

---

## How to Use:

1. Replace `[TOPIC_NAME]` with your topic (e.g., "The Dot Product")
2. Replace `[PROJECT_NAME]` with your folder name (e.g., "dot_product")
3. Attach: homework PDF, style_utils.py, common_issues.md, styling_guide.md
4. Run the prompt
5. Copy Block 1 to Cell 1, Block 2 to Cell 2, Block 3 to Cell 3, Block 4 to Cell 4
6. Run Cell 1 (setup), then Cell 2 (define all scenes)
7. Use Cell 3 to render individual scenes as needed
8. Use Cell 4 to concatenate all scenes into final video
