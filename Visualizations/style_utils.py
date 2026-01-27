from manim import *

# --- 1. COLOR PALETTE (From STYLING_GUIDE.md) ---
COLOR_VECTOR_A = BLUE
COLOR_VECTOR_B = RED
COLOR_RESULT = GREEN
COLOR_PROJECTION = YELLOW
COLOR_ANGLE_ARC = ORANGE
COLOR_HIGHLIGHT = GOLD
COLOR_GRID = GREY
COLOR_TEXT_PRIMARY = WHITE

# --- 2. SIZING STANDARDS ---
TITLE_SIZE = 48
SUBTITLE_SIZE = 36
FORMULA_SIZE = 40
LABEL_SIZE = 24

# --- 3. LAYOUT CONSTANTS ---
# Y-Ranges for Safe Zones
TITLE_Y_MIN = 3.0
FOOTER_Y_MAX = -2.5

class BaseScene(Scene):
    """
    The Foundation Class.
    Enforces the 'Safe Zone' layout automatically.
    """
    def setup_scene(self, title_text, subtitle_text=None):
        self.clear()

        # 1. Title (Top Safe Zone)
        self.title = Text(title_text, font_size=TITLE_SIZE, color=COLOR_TEXT_PRIMARY)
        self.title.to_edge(UP, buff=0.5)
        
        # Ensure title is above the safe line
        if self.title.get_bottom()[1] < TITLE_Y_MIN:
            self.title.set_y(3.5)

        self.play(Write(self.title, run_time=1))
        
        # 2. Subtitle (Optional)
        if subtitle_text:
            self.subtitle = Text(subtitle_text, font_size=SUBTITLE_SIZE, color=COLOR_HIGHLIGHT)
            self.subtitle.next_to(self.title, DOWN, buff=0.3)
            self.play(FadeIn(self.subtitle))
        
        self.wait(0.5)

    def get_standard_grid(self):
        """
        Returns a grid strictly confined to the Content Zone.
        Y range is -2.5 to 3.0 to prevent overlap.
        """
        grid = NumberPlane(
            x_range=[-7, 7, 1],
            y_range=[-3.5, 3.5, 1], # Reduced height to protect title
            x_length=14,
            y_length=7,
            background_line_style={
                "stroke_color": COLOR_GRID,
                "stroke_opacity": 0.3,
                "stroke_width": 1
            }
        ).add_coordinates()
        
        # Force grid to back so vectors sit on top
        grid.z_index = -1
        return grid

    def create_dynamic_box(self, mobject_group, color=COLOR_HIGHLIGHT):
        """
        Creates a box that automatically fits the content.
        """
        return SurroundingRectangle(
            mobject_group,
            color=color,
            buff=MED_LARGE_BUFF,
            fill_color=BLACK,
            fill_opacity=0.8,
            corner_radius=0.2
        )