"""
Manim Styling & Formatting Utilities
For Mathematical Education Videos
Version 1.1.0 - January 2026
"""

from manim import *

# ============================================================================
# COLOR PALETTE
# ============================================================================

# Core Vector Colors
COLOR_VECTOR_A = BLUE  # Primary vector (often the "base")
COLOR_VECTOR_B = RED  # Secondary vector
COLOR_VECTOR_C = PURPLE  # Tertiary vector (if needed)

# Operational Colors
COLOR_RESULT = GREEN  # Final answers, solutions
COLOR_PROJECTION = YELLOW  # Projected vectors, components
COLOR_ORTHOGONAL = PURPLE  # Perpendicular/orthogonal elements
COLOR_ANGLE_ARC = ORANGE  # Angle arcs and angle labels
COLOR_HIGHLIGHT = GOLD  # Key insights, important notes

# Structural Colors
COLOR_GRID = GREY  # Coordinate axes, grid lines
COLOR_BACKGROUND = BLACK  # Standard Manim background
COLOR_TEXT_PRIMARY = WHITE  # Main text
COLOR_TEXT_SECONDARY = GREY  # Supplementary text, captions

# Extended Palette
COLOR_QUATERNARY = TEAL
COLOR_QUINARY = PINK
COLOR_ERROR = RED_E  # For showing mistakes/corrections
COLOR_SUCCESS = GREEN_E  # For correct steps

# ============================================================================
# SCREEN PARTITIONING & LAYOUT ZONES
# ============================================================================

# Positioning Constants
POS_TITLE = UP * 3.5
POS_SUBTITLE = UP * 2.8
POS_GRID_CENTER = DOWN * 0.5  # Shift grid down to clear title

# Safe ranges
GRID_Y_RANGE = [-3.5, 3.5]  # NEVER exceed 3.5 to avoid title collision
GRID_X_RANGE = [-7, 7]

# ============================================================================
# SIZING STANDARDS
# ============================================================================

# Text Sizes
TITLE_SIZE = 48  # Scaled for 1080p
SUBTITLE_SIZE = 36  # Scene subtitles, section headers
FORMULA_SIZE = 40  # Primary mathematical formulas
FORMULA_SMALL = 28  # Secondary formulas, steps inside boxes
LABEL_SIZE = 24  # Vector labels, axis labels
ANNOTATION_SIZE = 20  # Small notes, dimensions

# Vector Properties
VECTOR_STROKE_WIDTH = 6  # Main vectors
VECTOR_TIP_LENGTH = 0.25  # Arrow tip size
VECTOR_TIP_WIDTH = 0.25  # Arrow tip width

AUXILIARY_STROKE_WIDTH = 3  # Dashed lines, construction lines
CONSTRUCTION_LINE_WIDTH = 2  # Very light helper lines

# Geometric Elements
ANGLE_RADIUS = 0.7  # Standard angle arc radius
ANGLE_RADIUS_SMALL = 0.4  # Tight spaces

# ============================================================================
# TIMING STANDARDS
# ============================================================================

# Animation Durations
WRITE_TIME = 1.0  # Writing text
DRAW_TIME = 1.5  # Drawing complex shapes
GROW_ARROW_TIME = 0.8  # Arrow growth
TRANSFORM_TIME = 1.5  # Morphing between objects

PAUSE_SHORT = 0.5  # Brief pause
PAUSE_MEDIUM = 1.0  # Standard pause
PAUSE_LONG = 2.0  # Emphasis pause
PAUSE_SCENE_END = 3.0  # End of scene


# ============================================================================
# BASE SCENE CLASS
# ============================================================================

class BaseScene(Scene):
    """
    Base class for all mathematical visualization scenes.
    Handles title and grid setup automatically.
    """

    def __init__(self, title="Mathematical Visualization", **kwargs):
        super().__init__(**kwargs)
        self.scene_title = title

    def setup(self):
        """Setup the scene with title"""
        super().setup()

    def construct(self):
        """Override this method in child classes"""
        pass

    def add_title(self, title_text=None):
        """Add title to the scene in the safe title zone"""
        if title_text is None:
            title_text = self.scene_title

        title = Text(title_text, font_size=TITLE_SIZE, color=COLOR_TEXT_PRIMARY)
        title.to_edge(UP, buff=0.3)

        # Ensure title stays in safe zone (Y > 3.0)
        if title.get_y() < 3.0:
            title.shift(UP * (3.0 - title.get_y() + 0.2))

        self.play(Write(title), run_time=WRITE_TIME)
        self.wait(PAUSE_SHORT)
        return title

    def get_standard_grid(self, x_range=None, y_range=None):
        """
        Create a standard grid that respects safe zones.

        Returns:
            NumberPlane: A properly configured grid
        """
        if x_range is None:
            x_range = GRID_X_RANGE + [1]  # Add step size
        if y_range is None:
            y_range = GRID_Y_RANGE + [1]  # Add step size

        # Calculate dimensions to fit within safe zones
        x_length = min(12, config.frame_width - 2)
        y_length = min(6, abs(y_range[1] - y_range[0]) * 1.0)

        axes = NumberPlane(
            x_range=x_range,
            y_range=y_range,
            x_length=x_length,
            y_length=y_length,
            background_line_style={
                "stroke_color": COLOR_GRID,
                "stroke_opacity": 0.3,
                "stroke_width": 1
            },
            axis_config={
                "stroke_color": COLOR_GRID,
                "stroke_width": 2,
                "include_numbers": True,
                "font_size": ANNOTATION_SIZE,
            }
        )

        # Shift grid down to content zone
        axes.shift(POS_GRID_CENTER)

        # Ensure grid doesn't exceed safe Y range
        if axes.get_top()[1] > 3.0:
            axes.shift(DOWN * (axes.get_top()[1] - 3.0 + 0.2))

        return axes

    def create_formula_box(self, *formulas, color=COLOR_HIGHLIGHT, position=DOWN * 2.5):
        """
        Create a dynamically-sized box for formulas.

        Args:
            *formulas: MathTex objects or strings
            color: Border color
            position: Where to place the box

        Returns:
            VGroup: Container with box and content
        """
        # Convert strings to MathTex if needed
        formula_objects = []
        for f in formulas:
            if isinstance(f, str):
                formula_objects.append(MathTex(f, font_size=FORMULA_SIZE))
            else:
                formula_objects.append(f)

        # Arrange formulas
        content = VGroup(*formula_objects).arrange(DOWN, buff=0.3)

        # Create dynamic box
        box = SurroundingRectangle(
            content,
            color=color,
            buff=MED_LARGE_BUFF,
            fill_color=BLACK,
            fill_opacity=0.9,
            corner_radius=0.1
        )

        # Group and position
        container = VGroup(box, content)
        container.move_to(position)

        return container

    def add_vector_with_label(self, start, end, color, label_text, label_position=None):
        """
        Create a vector arrow with a label.

        Args:
            start: Starting point
            end: Ending point
            color: Vector color
            label_text: Label text
            label_position: Where to place label (default: above vector)

        Returns:
            VGroup: Vector and label together
        """
        vector = Arrow(
            start=start,
            end=end,
            buff=0,
            color=color,
            stroke_width=VECTOR_STROKE_WIDTH,
            tip_length=VECTOR_TIP_LENGTH,
            max_tip_length_to_length_ratio=0.15
        )

        label = MathTex(label_text, font_size=LABEL_SIZE, color=color)
        label.add_background_rectangle(buff=0.1, opacity=0.8)

        if label_position is None:
            # Default: place at midpoint, offset perpendicular to vector
            mid = (np.array(start) + np.array(end)) / 2
            direction = np.array(end) - np.array(start)
            perp = np.array([-direction[1], direction[0], 0])
            perp = perp / np.linalg.norm(perp) if np.linalg.norm(perp) > 0 else UP
            label.move_to(mid + perp * 0.5)
        else:
            label.move_to(label_position)

        return VGroup(vector, label)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def add_background_to_text(text_obj, buff=0.1, opacity=0.8):
    """Add a background rectangle to text for readability"""
    return text_obj.add_background_rectangle(buff=buff, opacity=opacity)


def create_angle_arc(vertex, start_point, end_point, radius=ANGLE_RADIUS, color=COLOR_ANGLE_ARC):
    """
    Create an angle arc between two lines meeting at a vertex.

    Args:
        vertex: The point where lines meet
        start_point: Point on first line
        end_point: Point on second line
        radius: Arc radius
        color: Arc color

    Returns:
        Angle: The angle arc object
    """
    angle = Angle(
        Line(vertex, start_point),
        Line(vertex, end_point),
        radius=radius,
        color=color,
        stroke_width=AUXILIARY_STROKE_WIDTH
    )
    return angle