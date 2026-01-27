from manim import *

# --- 1. COLOR PALETTE (From STYLING_GUIDE.md) ---
COLOR_VECTOR_A = BLUE          # Primary vector
COLOR_VECTOR_B = RED           # Secondary vector
COLOR_RESULT = GREEN           # Final answers
COLOR_PROJECTION = YELLOW      # Projections
COLOR_ANGLE_ARC = ORANGE       # Angles
COLOR_HIGHLIGHT = GOLD         # Key insights
COLOR_GRID = GREY
COLOR_TEXT_PRIMARY = WHITE

# --- 2. SIZING STANDARDS ---
TITLE_SIZE = 48                # Scaled for 1080p
SUBTITLE_SIZE = 36
FORMULA_SIZE = 40
LABEL_SIZE = 28

# --- 3. THE BASE SCENE ---
class BaseScene(Scene):
    """
    All scenes must inherit from this class.
    It handles standard setup to ensure perfect alignment.
    """
    def setup_scene(self, title_text, subtitle_text=None):
        """
        Standardized title creation.
        """
        # 1. Clear any existing items (safety)
        self.clear()

        # 2. Create Title
        self.title = Text(title_text, font_size=TITLE_SIZE, color=COLOR_TEXT_PRIMARY)
        self.title.to_edge(UP, buff=0.5)
        
        # 3. Create Separator Line (optional but looks pro)
        self.separator = Line(LEFT*7, RIGHT*7, color=COLOR_GRID, stroke_width=2)
        self.separator.next_to(self.title, DOWN, buff=0.2)

        # 4. Animation
        self.play(
            Write(self.title, run_time=1),
            Create(self.separator, run_time=1)
        )
        self.wait(0.5)

        # 5. Handle Subtitle if present
        if subtitle_text:
            self.add_subtitle(subtitle_text)

    def add_subtitle(self, text):
        self.subtitle = Text(text, font_size=SUBTITLE_SIZE, color=COLOR_HIGHLIGHT)
        self.subtitle.next_to(self.separator, DOWN, buff=0.3)
        self.play(FadeIn(self.subtitle, shift=UP*0.2))
        self.wait(0.5)

    def get_standard_grid(self):
        """Returns a standardized number plane"""
        return NumberPlane(
            x_range=[-6, 6, 1],
            y_range=[-4, 4, 1],
            background_line_style={
                "stroke_color": COLOR_GRID,
                "stroke_width": 1,
                "stroke_opacity": 0.3
            }
        ).add_coordinates()