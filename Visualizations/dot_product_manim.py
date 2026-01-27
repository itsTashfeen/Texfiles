from manim import *
from style_utils import *  # Import our foundations

class Scene01_Introduction(BaseScene):
    """
    Scene 1: Introduction to the Dot Product.
    Contrast Algebraic vs Geometric definitions.
    """
    def construct(self):
        # 1. Standard Setup (Guarantees Alignment)
        self.setup_scene("The Dot Product")

        # 2. Algebraic Definition (Left Side)
        alg_title = Text("Algebraic", font_size=SUBTITLE_SIZE, color=BLUE)
        alg_formula = MathTex(
            r"\mathbf{a} \cdot \mathbf{b} = a_1b_1 + a_2b_2 + a_3b_3",
            font_size=FORMULA_SIZE
        )
        
        alg_group = VGroup(alg_title, alg_formula).arrange(DOWN, buff=0.5)
        alg_group.to_edge(LEFT, buff=1.5).shift(UP*0.5)

        # 3. Geometric Definition (Right Side)
        geo_title = Text("Geometric", font_size=SUBTITLE_SIZE, color=RED)
        geo_formula = MathTex(
            r"\mathbf{a} \cdot \mathbf{b} = |\mathbf{a}| |\mathbf{b}| \cos(\theta)",
            font_size=FORMULA_SIZE
        )
        
        geo_group = VGroup(geo_title, geo_formula).arrange(DOWN, buff=0.5)
        geo_group.to_edge(RIGHT, buff=1.5).shift(UP*0.5)

        # --- ANIMATION SEQUENCE ---
        
        # Show Algebraic
        self.play(Write(alg_title))
        self.play(Write(alg_formula))
        self.wait(1)

        # Show Geometric
        self.play(Write(geo_title))
        self.play(Write(geo_formula))
        self.wait(1)

        # 4. Key Insight (Bottom Center)
        insight_box = Rectangle(height=1.5, width=10, color=COLOR_HIGHLIGHT, fill_opacity=0.1)
        insight_text = Text(
            "Input: Two Vectors  →  Output: Scalar (Number)", 
            font_size=32, 
            color=WHITE
        )
        insight_group = VGroup(insight_box, insight_text).move_to(DOWN * 2)

        self.play(FadeIn(insight_group, shift=UP))
        self.wait(3)


class Scene03_GeometricVisualization(BaseScene):
    """
    Scene 3: Visualization of Problem 6 from Homework 12.3.
    |a|=4, |b|=8, theta=30 deg.
    """
    def construct(self):
        # 1. Standard Setup
        self.setup_scene("Geometric Interpretation")
        self.add_subtitle("Example: Problem 6")

        # 2. Setup Grid and Vectors
        grid = self.get_standard_grid()
        self.play(Create(grid), run_time=1.5)

        # Vector Data (Problem 6: |a|=4, |b|=8, angle=30)
        # We scale it down slightly to fit screen comfortably
        scale = 0.8 
        
        vec_a_start = ORIGIN
        vec_a_end = RIGHT * 4 * scale
        
        vec_b_start = ORIGIN
        # Calculate B coordinates: 8 * <cos30, sin30>
        vec_b_end = np.array([8 * np.cos(np.deg2rad(30)), 8 * np.sin(np.deg2rad(30)), 0]) * scale

        # Create Mobjects
        arrow_a = Arrow(vec_a_start, vec_a_end, color=COLOR_VECTOR_A, buff=0, stroke_width=6)
        label_a = MathTex(r"|\mathbf{a}| = 4", color=COLOR_VECTOR_A).next_to(arrow_a, DOWN)

        arrow_b = Arrow(vec_b_start, vec_b_end, color=COLOR_VECTOR_B, buff=0, stroke_width=6)
        label_b = MathTex(r"|\mathbf{b}| = 8", color=COLOR_VECTOR_B).next_to(arrow_b.get_end(), UP)

        # Angle Arc
        angle_arc = Angle(arrow_a, arrow_b, radius=1, color=COLOR_ANGLE_ARC)
        label_angle = MathTex(r"30^\circ", color=COLOR_ANGLE_ARC).next_to(angle_arc, RIGHT, buff=0.1).shift(UP*0.1)

        # --- ANIMATION SEQUENCE ---

        # Draw Vectors
        self.play(GrowArrow(arrow_a), Write(label_a))
        self.play(GrowArrow(arrow_b), Write(label_b))
        
        # Draw Angle
        self.play(Create(angle_arc), Write(label_angle))
        self.wait(1)

        # 3. Calculation Display (Overlay)
        calc_box = RoundedRectangle(corner_radius=0.2, height=3, width=5, color=GREY, fill_color=BLACK, fill_opacity=0.8)
        calc_box.to_corner(UL)
        
        step1 = MathTex(r"\mathbf{a} \cdot \mathbf{b} = |\mathbf{a}| |\mathbf{b}| \cos(\theta)")
        step2 = MathTex(r"= (4)(8) \cos(30^\circ)")
        step3 = MathTex(r"= 32 \left( \frac{\sqrt{3}}{2} \right)")
        step4 = MathTex(r"= 16\sqrt{3} \approx 27.7", color=COLOR_RESULT)

        calc_group = VGroup(step1, step2, step3, step4).arrange(DOWN, aligned_edge=LEFT)
        calc_group.move_to(calc_box)

        self.play(FadeIn(calc_box))
        self.play(Write(step1))
        self.wait(0.5)
        self.play(TransformMatchingTex(step1.copy(), step2))
        self.wait(0.5)
        self.play(TransformMatchingTex(step2.copy(), step3))
        self.wait(0.5)
        self.play(TransformMatchingTex(step3.copy(), step4))
        self.play(Indicate(step4, color=COLOR_RESULT))
        
        self.wait(3)