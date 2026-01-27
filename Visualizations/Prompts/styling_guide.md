```markdown
# Manim Styling & Formatting Guide
## For Mathematical Education Videos

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
```

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

---

## 📝 FORMULA FORMATTING

### LaTeX Best Practices
```latex
\vec{a}              # Named vectors
\langle 3, 4 \rangle # Component form
|\vec{a}|            # Magnitude
```

### Layout Strategy
1. **Define Content First:** Create the MathTex objects.
2. **Group:** Use `VGroup` to arrange them.
3. **Background:** Create `SurroundingRectangle` or `BackgroundRectangle` around the Group.
4. **Position:** Move the *Group* (the box will follow).

---

## 🔄 VERSION CONTROL

Current Version: **1.1.0** (Updated for Safe Zones & Dynamic Sizing)
Last Updated: January 2026