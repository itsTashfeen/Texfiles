# Manim Styling & Formatting Guide
## For Mathematical Education Videos
**Version 2.0 - Updated January 2026**

This document establishes the visual standards for all Manim mathematical visualization projects. Following these guidelines ensures consistency, professionalism, and optimal learning outcomes.

---

## 🎨 COLOR PALETTE

### Core Vector Colors
```python
COLOR_VECTOR_A = BLUE          # Primary vector (often the "base")
COLOR_VECTOR_B = RED           # Secondary vector
COLOR_VECTOR_C = PURPLE        # Tertiary vector (if needed)
```

**Rationale:** Blue and red are high-contrast and colorblind-friendly. Blue suggests "foundation," red suggests "action."

### Operational Colors
```python
COLOR_RESULT = GREEN           # Final answers, solutions
COLOR_PROJECTION = YELLOW      # Projected vectors, components
COLOR_ORTHOGONAL = PURPLE      # Perpendicular/orthogonal elements
COLOR_ANGLE_ARC = ORANGE       # Angle arcs and angle labels
COLOR_HIGHLIGHT = GOLD         # Key insights, important notes
```

### Structural Colors
```python
COLOR_GRID = GREY              # Coordinate axes, grid lines
COLOR_BACKGROUND = BLACK       # Standard Manim background
COLOR_TEXT_PRIMARY = WHITE     # Main text
COLOR_TEXT_SECONDARY = GREY    # Supplementary text, captions
```

### Extended Palette (for complex scenes)
```python
COLOR_QUATERNARY = TEAL
COLOR_QUINARY = PINK
COLOR_ERROR = RED_E            # For showing mistakes/corrections
COLOR_SUCCESS = GREEN_E        # For correct steps
```

---

## 📐 SCREEN PARTITIONING & LAYOUT ZONES (CRITICAL)

To prevent overlapping (e.g., arrows hitting titles), the screen is strictly divided.

### Vertical Zones (Y-Coordinates)
```
+---------------------------+  Y = +4.0
|       TITLE ZONE          |  (Title must stay above Y=3.0)
|---------------------------|  Y = +3.0
|                           |
|      CONTENT ZONE         |  (Grids/Vectors must stay between)
|                           |  (Y = -2.5 to Y = +3.0)
|                           |
|---------------------------|  Y = -2.5
|      FOOTER ZONE          |  (Formulas/Summaries go here)
+---------------------------+  Y = -4.0
```

### Positioning Constants
```python
# Absolute positions
POS_TITLE = UP * 3.5
POS_SUBTITLE = UP * 2.8
POS_GRID_CENTER = DOWN * 0.5   # Shift grid down to clear title

# Safe ranges
GRID_Y_RANGE = [-3.5, 3.5]     # NEVER exceed 3.5 to avoid title collision
GRID_X_RANGE = [-7, 7]
```

**⚠️ CRITICAL RULE:** All `NumberPlane` objects MUST have `y_range` that does not exceed [-3.5, 3.5] and MUST be shifted to content zone using `POS_GRID_CENTER`.

---

## 📏 SIZING STANDARDS

### Text Sizes
```python
TITLE_SIZE = 48               # Scaled for 1080p (Prevent overcrowding)
SUBTITLE_SIZE = 36            # Scene subtitles, section headers
FORMULA_SIZE = 40             # Primary mathematical formulas
FORMULA_SMALL = 28            # Secondary formulas, steps inside boxes
LABEL_SIZE = 24               # Vector labels, axis labels
ANNOTATION_SIZE = 20          # Small notes, dimensions
```

### Vector Properties
```python
VECTOR_STROKE_WIDTH = 6       # Main vectors
VECTOR_TIP_LENGTH = 0.25      # Arrow tip size
VECTOR_TIP_WIDTH = 0.25       # Arrow tip width

AUXILIARY_STROKE_WIDTH = 3    # Dashed lines, construction lines
CONSTRUCTION_LINE_WIDTH = 2   # Very light helper lines
```

### Geometric Elements
```python
ANGLE_RADIUS = 0.7            # Standard angle arc radius
ANGLE_RADIUS_SMALL = 0.4      # Tight spaces
```

---

## 🎯 AXIS & COORDINATE SYSTEM STANDARDS

### 2D Axes Configuration (Restricted Height)
```python
# Standard Grid Setup - Note the limited Y range to protect Title
axes_2d = NumberPlane(
    x_range=[-6, 6, 1],
    y_range=[-3.5, 3.5, 1],    # Restrict height!
    x_length=12,
    y_length=7,
    background_line_style={
        "stroke_color": COLOR_GRID,
        "stroke_opacity": 0.3,
        "stroke_width": 1
    }
).add_coordinates()

# MANDATORY: Shift to content zone
axes_2d.shift(POS_GRID_CENTER)
```

**Best Practice:** Use `BaseScene.get_standard_grid()` which handles all safety checks automatically.

### Axis Labels
```python
# Labels must have background to be readable over grid lines
label = MathTex("x").add_background_rectangle()
```

---

## 📦 CONTAINERS AND BACKGROUNDS

**Rule:** Never place text directly on a grid. Always use a background.

### Dynamic Boxing (Prevents Spills)
❌ **Bad (Fixed Size):**
```python
box = Rectangle(width=5, height=3) # Content might spill out!
```

✅ **Good (Dynamic Size):**
```python
content = VGroup(math_tex1, math_tex2).arrange(DOWN)
box = SurroundingRectangle(
    content, 
    color=COLOR_HIGHLIGHT, 
    buff=MED_LARGE_BUFF,
    fill_color=BLACK, 
    fill_opacity=0.8
)
self.play(Create(box), Write(content))
```

**Best Practice:** Use `BaseScene.create_formula_box()` helper method.

---

## ⏱️ TIMING STANDARDS

### Animation Durations
```python
WRITE_TIME = 1.0              # Writing text
DRAW_TIME = 1.5               # Drawing complex shapes
GROW_ARROW_TIME = 0.8         # Arrow growth
TRANSFORM_TIME = 1.5          # Morphing between objects

PAUSE_SHORT = 0.5             # Brief pause
PAUSE_MEDIUM = 1.0            # Standard pause
PAUSE_LONG = 2.0              # Emphasis pause
PAUSE_SCENE_END = 3.0         # End of scene
```

### Rhythm Guidelines
1. **Introduce → Demonstrate → Emphasize → Pause**
2. Never stack animations without at least 0.3s pause
3. Complex calculations: 1.5s per step minimum
4. Final results: 2-3s hold time

**Target Scene Length:** 60-70 seconds per scene

---

## 📝 FORMULA FORMATTING

### LaTeX Best Practices
```latex
\vec{a}              # Named vectors
\langle 3, 4 \rangle # Component form
|\vec{a}|            # Magnitude
\cdot                # Dot product
\times               # Cross product
```

### Layout Strategy
1. **Define Content First:** Create the MathTex objects.
2. **Group:** Use `VGroup` to arrange them.
3. **Background:** Create `SurroundingRectangle` or `BackgroundRectangle` around the Group.
4. **Position:** Move the *Group* (the box will follow).

---

## 🎬 SCENE STRUCTURE TEMPLATE

Every scene should follow this structure:

```python
class SceneXX_Name(BaseScene):
    def __init__(self, **kwargs):
        super().__init__(title="Scene Title", **kwargs)
    
    def construct(self):
        # [0-5s] Title
        title = self.add_title("Scene Title")
        self.wait(PAUSE_MEDIUM)
        
        # [5-15s] Setup/Introduction
        # Introduce the problem or concept
        
        # [15-45s] Main Content
        # Core visualization in CONTENT ZONE
        
        # [45-60s] Summary/Conclusion
        # Key takeaway in FOOTER ZONE
        
        # [60-65s] Final pause
        self.wait(PAUSE_SCENE_END)
```

---

## 🚫 COMMON MISTAKES TO AVOID

1. **Grid Too Tall:** Y-range exceeds 3.5 → overlaps title
2. **Text Without Background:** Unreadable over grid lines
3. **Fixed-Size Boxes:** Content spills outside rectangle
4. **Rushed Pacing:** Animations stack without pauses
5. **Inconsistent Colors:** Using random colors instead of palette
6. **Missing Labels:** Vectors without identification
7. **Footer Overflow:** Formulas placed above Y = -2.5

---

## ✅ QUALITY CHECKLIST

Before finalizing any scene:

- [ ] Title stays above Y = 3.0
- [ ] Grid Y-range does not exceed [-3.5, 3.5]
- [ ] Grid shifted with `POS_GRID_CENTER` or `DOWN * 0.5`
- [ ] All text over grids has background rectangle
- [ ] Colors follow palette (Blue/Red/Green/Yellow/Orange)
- [ ] Font sizes match standards (48/36/40/28/24/20)
- [ ] Animations have proper pauses (0.5s/1s/2s/3s)
- [ ] Scene length is 60-70 seconds
- [ ] Dynamic boxes used for formulas (no fixed sizes)
- [ ] All vectors have labels with background

---

## 📚 HELPER METHODS REFERENCE

### BaseScene Methods

```python
# Add title (automatically in safe zone)
title = self.add_title("Title Text")

# Get safe grid (Y-restricted, auto-shifted)
grid = self.get_standard_grid()

# Create dynamic formula box
box = self.create_formula_box(formula1, formula2, position=DOWN*2.5)

# Add labeled vector
vector = self.add_vector_with_label(start, end, COLOR_VECTOR_A, r"\vec{a}")
```

### Utility Functions

```python
# Add background to any text
add_background_to_text(text_obj, buff=0.1, opacity=0.8)

# Create angle arc
arc = create_angle_arc(vertex, start_point, end_point, radius=ANGLE_RADIUS)
```

---

## 📄 VERSION CONTROL

**Current Version:** 2.0  
**Last Updated:** January 2026  
**Changes from 1.1:**
- Added consolidated scene block workflow
- Added FFmpeg concatenation guidelines
- Added quality checklist
- Added common mistakes section
- Updated helper methods reference

---

## 📞 TROUBLESHOOTING

See `common_issues.md` for detailed solutions to known problems.

Quick reminders:
- Grid overlapping title → Use `get_standard_grid()`
- Text unreadable → Add `.add_background_rectangle()`
- Videos wrong location → Check Cell 1 setup
- Import errors → Check absolute path in `sys.path.append()`

---

**End of Styling Guide**
