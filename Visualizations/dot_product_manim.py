"""
Comprehensive Dot Product Visualization using Manim Community
Based on Homework 12.3: The Dot Product

This script creates educational animations covering:
1. Introduction to dot product (algebraic and geometric)
2. Component-wise calculation
3. Geometric interpretation with angles
4. Orthogonality
5. Projections (scalar and vector)
6. Real-world applications

Author: Generated for Tashfeen Omran
Date: January 2026
"""

from manim import *
import numpy as np

# ==================== CONFIGURATION ====================
# Color scheme for consistent styling
COLOR_VECTOR_A = BLUE
COLOR_VECTOR_B = RED
COLOR_RESULT = GREEN
COLOR_PROJECTION = YELLOW
COLOR_ORTHOGONAL = PURPLE
COLOR_ANGLE_ARC = ORANGE
COLOR_GRID = GREY
COLOR_HIGHLIGHT = GOLD

# Text styling
TITLE_SCALE = 1.0
SUBTITLE_SCALE = 0.8
FORMULA_SCALE = 0.9
LABEL_SCALE = 0.7


# ==================== SCENE 1: INTRODUCTION ====================
class Scene01_Introduction(Scene):
    """
    Introduction to the dot product concept
    Shows the definition and basic properties
    """

    def construct(self):
        # Title
        title = Text("The Dot Product", font_size=60, weight=BOLD)
        title.to_edge(UP)
        subtitle = Text("(Scalar Product)", font_size=36, color=GREY)
        subtitle.next_to(title, DOWN)

        self.play(Write(title))
        self.play(FadeIn(subtitle))
        self.wait(2)

        # Move title up
        self.play(
            title.animate.scale(0.6).to_edge(UP, buff=0.3),
            FadeOut(subtitle)
        )

        # Definition box
        definition = VGroup(
            Text("Definition:", font_size=36, color=YELLOW),
            MathTex(
                r"\vec{a} \cdot \vec{b} = a_1 b_1 + a_2 b_2 + a_3 b_3",
                font_size=44
            ),
            Text("(Algebraic Definition)", font_size=28, color=GREY)
        ).arrange(DOWN, buff=0.3)
        definition.shift(UP * 1.5)

        self.play(Write(definition[0]))
        self.play(Write(definition[1]))
        self.play(FadeIn(definition[2]))
        self.wait(2)

        # Geometric definition
        geometric = VGroup(
            MathTex(
                r"\vec{a} \cdot \vec{b} = |\vec{a}| |\vec{b}| \cos \theta",
                font_size=44
            ),
            Text("(Geometric Definition)", font_size=28, color=GREY)
        ).arrange(DOWN, buff=0.3)
        geometric.shift(DOWN * 0.5)

        self.play(Write(geometric[0]))
        self.play(FadeIn(geometric[1]))
        self.wait(2)

        # Key insight
        insight = Text(
            "The dot product converts two vectors into a scalar!",
            font_size=32,
            color=COLOR_HIGHLIGHT,
            weight=BOLD
        ).to_edge(DOWN, buff=0.5)

        self.play(Write(insight))
        self.wait(3)

        # Clear for next scene
        self.play(
            *[FadeOut(mob) for mob in self.mobjects]
        )


# ==================== SCENE 2: ALGEBRAIC CALCULATION ====================
class Scene02_AlgebraicCalculation(Scene):
    """
    Demonstrates the component-wise calculation of dot product
    Example: a = <3, 4>, b = <2, 1>
    """

    def construct(self):
        # Title
        title = Text("Algebraic Calculation", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait()

        # Define vectors
        vec_a_text = MathTex(r"\vec{a} = \langle 3, 4 \rangle", color=COLOR_VECTOR_A)
        vec_b_text = MathTex(r"\vec{b} = \langle 2, 1 \rangle", color=COLOR_VECTOR_B)
        vectors = VGroup(vec_a_text, vec_b_text).arrange(RIGHT, buff=2)
        vectors.shift(UP * 2)

        self.play(Write(vec_a_text), Write(vec_b_text))
        self.wait()

        # Show formula
        formula = MathTex(
            r"\vec{a} \cdot \vec{b} = a_1 b_1 + a_2 b_2",
            font_size=40
        ).shift(UP * 0.5)

        self.play(Write(formula))
        self.wait()

        # Step-by-step calculation
        step1 = MathTex(
            r"= (3)(2) + (4)(1)",
            font_size=40
        ).next_to(formula, DOWN, buff=0.5)

        self.play(Write(step1))
        self.wait()

        # Highlight multiplication
        rect1 = SurroundingRectangle(step1[0][1:4], color=YELLOW, buff=0.1)
        rect2 = SurroundingRectangle(step1[0][6:9], color=YELLOW, buff=0.1)

        self.play(Create(rect1), Create(rect2))
        self.wait()
        self.play(FadeOut(rect1), FadeOut(rect2))

        step2 = MathTex(
            r"= 6 + 4",
            font_size=40
        ).next_to(step1, DOWN, buff=0.5)

        self.play(Write(step2))
        self.wait()

        step3 = MathTex(
            r"= 10",
            font_size=40,
            color=COLOR_RESULT
        ).next_to(step2, DOWN, buff=0.5)

        result_box = SurroundingRectangle(step3, color=COLOR_RESULT, buff=0.2)

        self.play(Write(step3))
        self.play(Create(result_box))
        self.wait(2)

        # Key insight
        insight = Text(
            "Component-wise multiply, then sum!",
            font_size=32,
            color=COLOR_HIGHLIGHT
        ).to_edge(DOWN, buff=0.5)

        self.play(Write(insight))
        self.wait(3)

        self.play(*[FadeOut(mob) for mob in self.mobjects])


# ==================== SCENE 3: GEOMETRIC VISUALIZATION ====================
class Scene03_GeometricVisualization(Scene):
    """
    Shows vectors geometrically and visualizes the dot product
    using the angle between them
    """

    def construct(self):
        # Title
        title = Text("Geometric Interpretation", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))

        # Create coordinate system
        axes = Axes(
            x_range=[-1, 5, 1],
            y_range=[-1, 5, 1],
            x_length=6,
            y_length=6,
            axis_config={"include_tip": True, "include_numbers": True},
        ).shift(DOWN * 0.5)

        axes_labels = axes.get_axis_labels(x_label="x", y_label="y")

        self.play(Create(axes), Write(axes_labels))
        self.wait()

        # Define vectors (same as algebraic example)
        vec_a = Arrow(
            axes.c2p(0, 0),
            axes.c2p(3, 4),
            buff=0,
            color=COLOR_VECTOR_A,
            stroke_width=6
        )
        vec_b = Arrow(
            axes.c2p(0, 0),
            axes.c2p(2, 1),
            buff=0,
            color=COLOR_VECTOR_B,
            stroke_width=6
        )

        label_a = MathTex(r"\vec{a}", color=COLOR_VECTOR_A).next_to(
            vec_a.get_end(), RIGHT, buff=0.2
        )
        label_b = MathTex(r"\vec{b}", color=COLOR_VECTOR_B).next_to(
            vec_b.get_end(), UP, buff=0.2
        )

        self.play(GrowArrow(vec_a), Write(label_a))
        self.play(GrowArrow(vec_b), Write(label_b))
        self.wait()

        # Show angle between vectors
        angle = Angle(
            vec_b, vec_a,
            radius=0.8,
            color=COLOR_ANGLE_ARC,
            other_angle=False
        )
        angle_label = MathTex(r"\theta", color=COLOR_ANGLE_ARC).move_to(
            Angle(vec_b, vec_a, radius=1.2).point_from_proportion(0.5)
        )

        self.play(Create(angle), Write(angle_label))
        self.wait(2)

        # Calculate angle
        # For a = <3, 4>, b = <2, 1>: dot product = 10
        # |a| = 5, |b| = sqrt(5)
        # cos(theta) = 10 / (5 * sqrt(5)) = 2/sqrt(5)
        # theta ≈ 26.57 degrees

        # Show formula
        formula = MathTex(
            r"\vec{a} \cdot \vec{b} = |\vec{a}| |\vec{b}| \cos \theta",
            font_size=36
        ).to_corner(UL, buff=0.5).shift(DOWN * 1.2)

        self.play(Write(formula))
        self.wait()

        # Show magnitudes
        mag_a_line = DashedLine(
            axes.c2p(0, 0),
            axes.c2p(3, 4),
            color=COLOR_VECTOR_A,
            stroke_width=3
        )
        mag_a_label = MathTex(
            r"|\vec{a}| = 5",
            color=COLOR_VECTOR_A,
            font_size=28
        ).next_to(formula, DOWN, aligned_edge=LEFT, buff=0.3)

        self.play(Create(mag_a_line))
        self.play(Write(mag_a_label))
        self.wait()

        mag_b_line = DashedLine(
            axes.c2p(0, 0),
            axes.c2p(2, 1),
            color=COLOR_VECTOR_B,
            stroke_width=3
        )
        mag_b_label = MathTex(
            r"|\vec{b}| = \sqrt{5}",
            color=COLOR_VECTOR_B,
            font_size=28
        ).next_to(mag_a_label, DOWN, aligned_edge=LEFT, buff=0.2)

        self.play(Create(mag_b_line))
        self.play(Write(mag_b_label))
        self.wait()

        # Calculate and show result
        calc = MathTex(
            r"\vec{a} \cdot \vec{b} = 5 \cdot \sqrt{5} \cdot \cos(26.57°) = 10",
            font_size=32,
            color=COLOR_RESULT
        ).next_to(mag_b_label, DOWN, aligned_edge=LEFT, buff=0.3)

        self.play(Write(calc))
        self.wait(3)

        self.play(*[FadeOut(mob) for mob in self.mobjects])


# ==================== SCENE 4: PROJECTION VISUALIZATION ====================
class Scene04_Projections(Scene):
    """
    Visualizes scalar and vector projections
    Shows comp_a(b) and proj_a(b)
    """

    def construct(self):
        # Title
        title = Text("Projections", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))

        # Create axes
        axes = Axes(
            x_range=[-1, 6, 1],
            y_range=[-1, 4, 1],
            x_length=7,
            y_length=5,
            axis_config={"include_tip": True},
        ).shift(DOWN * 0.8)

        self.play(Create(axes))
        self.wait()

        # Define vectors
        vec_a = Arrow(
            axes.c2p(0, 0),
            axes.c2p(4, 1),
            buff=0,
            color=COLOR_VECTOR_A,
            stroke_width=6
        )
        vec_b = Arrow(
            axes.c2p(0, 0),
            axes.c2p(3, 3),
            buff=0,
            color=COLOR_VECTOR_B,
            stroke_width=6
        )

        label_a = MathTex(r"\vec{a}", color=COLOR_VECTOR_A).next_to(
            vec_a.get_end(), DOWN, buff=0.2
        )
        label_b = MathTex(r"\vec{b}", color=COLOR_VECTOR_B).next_to(
            vec_b.get_end(), UP, buff=0.2
        )

        self.play(GrowArrow(vec_a), Write(label_a))
        self.play(GrowArrow(vec_b), Write(label_b))
        self.wait()

        # Calculate projection
        # a = <4, 1>, b = <3, 3>
        # a · b = 12 + 3 = 15
        # |a| = sqrt(17)
        # comp_a(b) = 15/sqrt(17)
        # proj_a(b) = (15/17) * <4, 1>

        a_np = np.array([4, 1, 0])
        b_np = np.array([3, 3, 0])
        dot_product = np.dot(a_np, b_np)
        mag_a = np.linalg.norm(a_np)
        scalar_proj = dot_product / mag_a
        vector_proj = (dot_product / (mag_a ** 2)) * a_np

        # Show perpendicular drop
        proj_point = axes.c2p(vector_proj[0], vector_proj[1])
        perp_line = DashedLine(
            vec_b.get_end(),
            proj_point,
            color=COLOR_ORTHOGONAL,
            stroke_width=3
        )

        self.play(Create(perp_line))
        self.wait()

        # Show vector projection
        vec_proj = Arrow(
            axes.c2p(0, 0),
            proj_point,
            buff=0,
            color=COLOR_PROJECTION,
            stroke_width=6
        )

        label_proj = MathTex(
            r"\text{proj}_{\vec{a}} \vec{b}",
            color=COLOR_PROJECTION,
            font_size=32
        ).next_to(vec_proj, DOWN, buff=0.3)

        self.play(GrowArrow(vec_proj), Write(label_proj))
        self.wait()

        # Show formulas
        formula_box = VGroup(
            MathTex(
                r"\text{comp}_{\vec{a}} \vec{b} = \frac{\vec{a} \cdot \vec{b}}{|\vec{a}|}",
                font_size=32
            ),
            MathTex(
                r"\text{proj}_{\vec{a}} \vec{b} = \frac{\vec{a} \cdot \vec{b}}{|\vec{a}|^2} \vec{a}",
                font_size=32
            )
        ).arrange(DOWN, buff=0.4).to_corner(UR, buff=0.5)

        formula_box[0].set_color(YELLOW)
        formula_box[1].set_color(COLOR_PROJECTION)

        self.play(Write(formula_box))
        self.wait(2)

        # Highlight: projection is parallel to a
        parallel_text = Text(
            "Projection is parallel to",
            font_size=28,
            color=WHITE
        ).to_edge(DOWN, buff=1.2)
        parallel_a = MathTex(r"\vec{a}", color=COLOR_VECTOR_A, font_size=32).next_to(
            parallel_text, RIGHT, buff=0.2
        )

        self.play(Write(parallel_text), Write(parallel_a))
        self.wait(3)

        self.play(*[FadeOut(mob) for mob in self.mobjects])


# ==================== SCENE 5: ORTHOGONALITY ====================
class Scene05_Orthogonality(Scene):
    """
    Demonstrates orthogonal (perpendicular) vectors
    Shows that dot product = 0 when vectors are perpendicular
    """

    def construct(self):
        # Title
        title = Text("Orthogonality", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))

        # Subtitle
        subtitle = Text(
            "When vectors are perpendicular",
            font_size=32,
            color=GREY
        ).next_to(title, DOWN, buff=0.3)
        self.play(FadeIn(subtitle))
        self.wait()

        # Create axes
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
            x_length=8,
            y_length=8,
            axis_config={"include_tip": True},
        ).shift(DOWN * 0.3)

        self.play(Create(axes))
        self.wait()

        # Define perpendicular vectors
        vec_a = Arrow(
            axes.c2p(0, 0),
            axes.c2p(3, 0),
            buff=0,
            color=COLOR_VECTOR_A,
            stroke_width=6
        )
        vec_b = Arrow(
            axes.c2p(0, 0),
            axes.c2p(0, 3),
            buff=0,
            color=COLOR_VECTOR_B,
            stroke_width=6
        )

        label_a = MathTex(r"\vec{a} = \langle 3, 0 \rangle", color=COLOR_VECTOR_A).next_to(
            vec_a.get_end(), DOWN, buff=0.3
        )
        label_b = MathTex(r"\vec{b} = \langle 0, 3 \rangle", color=COLOR_VECTOR_B).next_to(
            vec_b.get_end(), LEFT, buff=0.3
        )

        self.play(GrowArrow(vec_a), Write(label_a))
        self.play(GrowArrow(vec_b), Write(label_b))
        self.wait()

        # Show right angle
        right_angle = RightAngle(
            Line(axes.c2p(0, 0), axes.c2p(1, 0)),
            Line(axes.c2p(0, 0), axes.c2p(0, 1)),
            length=0.3,
            color=COLOR_ANGLE_ARC
        )

        self.play(Create(right_angle))
        self.wait()

        # Calculate dot product
        calc_box = VGroup(
            MathTex(
                r"\vec{a} \cdot \vec{b} = (3)(0) + (0)(3)",
                font_size=36
            ),
            MathTex(
                r"= 0",
                font_size=40,
                color=COLOR_RESULT
            )
        ).arrange(DOWN, buff=0.4).to_corner(UL, buff=0.7).shift(DOWN * 1.5)

        self.play(Write(calc_box[0]))
        self.wait()
        self.play(Write(calc_box[1]))

        result_rect = SurroundingRectangle(calc_box[1], color=COLOR_RESULT, buff=0.15)
        self.play(Create(result_rect))
        self.wait(2)

        # Key theorem
        theorem = VGroup(
            Text("Key Theorem:", font_size=32, color=YELLOW, weight=BOLD),
            MathTex(
                r"\vec{a} \perp \vec{b} \iff \vec{a} \cdot \vec{b} = 0",
                font_size=36
            )
        ).arrange(DOWN, buff=0.3).to_edge(DOWN, buff=0.7)

        self.play(Write(theorem))
        self.wait(3)

        # Show another example
        self.play(
            *[FadeOut(mob) for mob in [vec_a, vec_b, label_a, label_b, right_angle, calc_box, result_rect]]
        )

        # Non-obvious perpendicular vectors
        vec_c = Arrow(
            axes.c2p(0, 0),
            axes.c2p(2, 3),
            buff=0,
            color=COLOR_VECTOR_A,
            stroke_width=6
        )
        vec_d = Arrow(
            axes.c2p(0, 0),
            axes.c2p(3, -2),
            buff=0,
            color=COLOR_VECTOR_B,
            stroke_width=6
        )

        label_c = MathTex(r"\vec{c} = \langle 2, 3 \rangle", color=COLOR_VECTOR_A).next_to(
            vec_c.get_end(), UP, buff=0.2
        )
        label_d = MathTex(r"\vec{d} = \langle 3, -2 \rangle", color=COLOR_VECTOR_B).next_to(
            vec_d.get_end(), DOWN, buff=0.2
        )

        self.play(GrowArrow(vec_c), Write(label_c))
        self.play(GrowArrow(vec_d), Write(label_d))
        self.wait()

        # Show calculation
        calc2 = VGroup(
            MathTex(
                r"\vec{c} \cdot \vec{d} = (2)(3) + (3)(-2)",
                font_size=36
            ),
            MathTex(
                r"= 6 - 6 = 0",
                font_size=36
            ),
            Text("Therefore, perpendicular!", font_size=28, color=COLOR_RESULT)
        ).arrange(DOWN, buff=0.3).to_corner(UR, buff=0.5)

        self.play(Write(calc2))
        self.wait(3)

        self.play(*[FadeOut(mob) for mob in self.mobjects])


# ==================== SCENE 6: ANGLE CALCULATION ====================
class Scene06_AngleCalculation(Scene):
    """
    Shows how to find the angle between two vectors
    using the dot product formula
    """

    def construct(self):
        # Title
        title = Text("Finding Angles Between Vectors", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))

        # Create axes
        axes = Axes(
            x_range=[-1, 5, 1],
            y_range=[-1, 4, 1],
            x_length=6,
            y_length=5,
            axis_config={"include_tip": True},
        ).shift(DOWN * 0.5)

        self.play(Create(axes))

        # Define vectors
        vec_a = Arrow(
            axes.c2p(0, 0),
            axes.c2p(4, 2),
            buff=0,
            color=COLOR_VECTOR_A,
            stroke_width=6
        )
        vec_b = Arrow(
            axes.c2p(0, 0),
            axes.c2p(2, 3),
            buff=0,
            color=COLOR_VECTOR_B,
            stroke_width=6
        )

        label_a = MathTex(r"\vec{a} = \langle 4, 2 \rangle", color=COLOR_VECTOR_A).next_to(
            vec_a.get_end(), RIGHT, buff=0.2
        )
        label_b = MathTex(r"\vec{b} = \langle 2, 3 \rangle", color=COLOR_VECTOR_B).next_to(
            vec_b.get_end(), UP, buff=0.2
        )

        self.play(GrowArrow(vec_a), Write(label_a))
        self.play(GrowArrow(vec_b), Write(label_b))
        self.wait()

        # Show angle
        angle = Angle(
            vec_a, vec_b,
            radius=0.7,
            color=COLOR_ANGLE_ARC
        )
        angle_label = MathTex(r"\theta = ?", color=COLOR_ANGLE_ARC).move_to(
            Angle(vec_a, vec_b, radius=1.1).point_from_proportion(0.5)
        )

        self.play(Create(angle), Write(angle_label))
        self.wait()

        # Show formula derivation
        steps = VGroup(
            MathTex(
                r"\cos \theta = \frac{\vec{a} \cdot \vec{b}}{|\vec{a}| |\vec{b}|}",
                font_size=32
            ),
            MathTex(
                r"= \frac{(4)(2) + (2)(3)}{\sqrt{20} \cdot \sqrt{13}}",
                font_size=32
            ),
            MathTex(
                r"= \frac{14}{\sqrt{260}}",
                font_size=32
            ),
            MathTex(
                r"\theta = \arccos\left(\frac{14}{\sqrt{260}}\right) \approx 29.74°",
                font_size=32,
                color=COLOR_RESULT
            )
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3).to_corner(UL, buff=0.5).shift(DOWN * 1)

        for i, step in enumerate(steps):
            self.play(Write(step))
            self.wait(1.5 if i < len(steps) - 1 else 2)

        # Highlight result
        result_box = SurroundingRectangle(steps[-1], color=COLOR_RESULT, buff=0.1)
        self.play(Create(result_box))
        self.wait(3)

        self.play(*[FadeOut(mob) for mob in self.mobjects])


# ==================== SCENE 7: WORK APPLICATION ====================
class Scene07_WorkApplication(Scene):
    """
    Real-world application: Work done by a force
    W = F · d
    """

    def construct(self):
        # Title
        title = Text("Real-World Application: Work", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))

        # Setup
        ground = Line(LEFT * 5, RIGHT * 5, color=GREY).shift(DOWN * 2)
        self.play(Create(ground))

        # Object (box)
        box = Square(side_length=0.8, color=BLUE, fill_opacity=0.7).shift(DOWN * 1.6)
        box_label = Text("Box", font_size=24).move_to(box.get_center())

        self.play(Create(box), Write(box_label))
        self.wait()

        # Force vector (angled)
        force_start = box.get_right()
        force_end = force_start + np.array([2, 1, 0])
        force_arrow = Arrow(
            force_start,
            force_end,
            buff=0,
            color=RED,
            stroke_width=6
        )
        force_label = MathTex(r"\vec{F}", color=RED).next_to(force_end, UP, buff=0.1)

        self.play(GrowArrow(force_arrow), Write(force_label))
        self.wait()

        # Displacement vector
        displacement_arrow = Arrow(
            box.get_center(),
            box.get_center() + RIGHT * 3,
            buff=0,
            color=GREEN,
            stroke_width=6
        )
        displacement_label = MathTex(r"\vec{d}", color=GREEN).next_to(
            displacement_arrow.get_end(), DOWN, buff=0.2
        )

        self.play(GrowArrow(displacement_arrow), Write(displacement_label))
        self.wait()

        # Show angle
        angle = Angle(
            displacement_arrow,
            Line(force_start, force_end),
            radius=0.5,
            color=COLOR_ANGLE_ARC
        )
        angle_label = MathTex(r"\theta", color=COLOR_ANGLE_ARC, font_size=28).next_to(
            angle, RIGHT, buff=0.1
        )

        self.play(Create(angle), Write(angle_label))
        self.wait()

        # Work formula
        formula_box = VGroup(
            Text("Work Done:", font_size=32, color=YELLOW, weight=BOLD),
            MathTex(
                r"W = \vec{F} \cdot \vec{d}",
                font_size=40
            ),
            MathTex(
                r"= |\vec{F}| |\vec{d}| \cos \theta",
                font_size=36
            )
        ).arrange(DOWN, buff=0.3).to_corner(UR, buff=0.5)

        self.play(Write(formula_box))
        self.wait(2)

        # Example calculation
        example = VGroup(
            Text("Example:", font_size=28, color=GREY),
            MathTex(r"|\vec{F}| = 20 \text{ N}", font_size=28),
            MathTex(r"|\vec{d}| = 10 \text{ m}", font_size=28),
            MathTex(r"\theta = 30°", font_size=28),
            MathTex(
                r"W = 20 \cdot 10 \cdot \cos(30°) = 173.2 \text{ J}",
                font_size=28,
                color=COLOR_RESULT
            )
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.2).to_edge(LEFT, buff=0.5).shift(UP * 1)

        self.play(Write(example))
        self.wait(3)

        # Key insight
        insight = Text(
            "Only the component of force parallel to displacement does work!",
            font_size=28,
            color=COLOR_HIGHLIGHT
        ).to_edge(DOWN, buff=0.5)

        self.play(Write(insight))
        self.wait(3)

        self.play(*[FadeOut(mob) for mob in self.mobjects])


# ==================== SCENE 8: SUMMARY ====================
class Scene08_Summary(Scene):
    """
    Summary of key concepts and formulas
    """

    def construct(self):
        # Title
        title = Text("Summary: The Dot Product", font_size=52, weight=BOLD)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait()

        # Key formulas
        formulas = VGroup(
            VGroup(
                Text("1. Algebraic:", font_size=32, color=YELLOW),
                MathTex(
                    r"\vec{a} \cdot \vec{b} = a_1 b_1 + a_2 b_2 + a_3 b_3",
                    font_size=36
                )
            ).arrange(RIGHT, buff=0.5),

            VGroup(
                Text("2. Geometric:", font_size=32, color=YELLOW),
                MathTex(
                    r"\vec{a} \cdot \vec{b} = |\vec{a}| |\vec{b}| \cos \theta",
                    font_size=36
                )
            ).arrange(RIGHT, buff=0.5),

            VGroup(
                Text("3. Angle:", font_size=32, color=YELLOW),
                MathTex(
                    r"\cos \theta = \frac{\vec{a} \cdot \vec{b}}{|\vec{a}| |\vec{b}|}",
                    font_size=36
                )
            ).arrange(RIGHT, buff=0.5),

            VGroup(
                Text("4. Orthogonality:", font_size=32, color=YELLOW),
                MathTex(
                    r"\vec{a} \perp \vec{b} \iff \vec{a} \cdot \vec{b} = 0",
                    font_size=36
                )
            ).arrange(RIGHT, buff=0.5),

            VGroup(
                Text("5. Projection:", font_size=32, color=YELLOW),
                MathTex(
                    r"\text{proj}_{\vec{a}} \vec{b} = \frac{\vec{a} \cdot \vec{b}}{|\vec{a}|^2} \vec{a}",
                    font_size=36
                )
            ).arrange(RIGHT, buff=0.5)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5).shift(DOWN * 0.5)

        for formula in formulas:
            self.play(Write(formula))
            self.wait(1)

        self.wait(2)

        # Key insights box
        insights = VGroup(
            Text("Key Insights:", font_size=36, color=COLOR_HIGHLIGHT, weight=BOLD),
            Text("• Dot product converts vectors to scalars", font_size=28),
            Text("• Measures how much vectors 'align'", font_size=28),
            Text("• Zero when perpendicular", font_size=28),
            Text("• Used in projections, work, and more", font_size=28)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.25).to_edge(DOWN, buff=0.5)

        self.play(FadeIn(insights))
        self.wait(4)

        # Fade all
        self.play(*[FadeOut(mob) for mob in self.mobjects])

        # Final message
        final = Text(
            "Master the dot product - it's fundamental to vector calculus!",
            font_size=40,
            color=COLOR_HIGHLIGHT,
            weight=BOLD
        )
        self.play(Write(final))
        self.wait(3)
        self.play(FadeOut(final))


# ==================== SCENE 9: INTERACTIVE ANGLE DEMO ====================
class Scene09_InteractiveAngle(Scene):
    """
    Shows how dot product changes as angle changes
    Demonstrates the cos(theta) relationship
    """

    def construct(self):
        # Title
        title = Text("How Dot Product Changes with Angle", font_size=44)
        title.to_edge(UP)
        self.add(title)

        # Create axes
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
            x_length=8,
            y_length=8,
            axis_config={"include_tip": True},
        ).shift(DOWN * 0.3)

        self.add(axes)

        # Fixed vector a
        vec_a = Arrow(
            axes.c2p(0, 0),
            axes.c2p(3, 0),
            buff=0,
            color=COLOR_VECTOR_A,
            stroke_width=6
        )
        label_a = MathTex(r"\vec{a}", color=COLOR_VECTOR_A).next_to(
            vec_a.get_end(), DOWN, buff=0.2
        )

        self.add(vec_a, label_a)

        # Rotating vector b
        angle_tracker = ValueTracker(0)

        vec_b = always_redraw(lambda: Arrow(
            axes.c2p(0, 0),
            axes.c2p(
                3 * np.cos(angle_tracker.get_value()),
                3 * np.sin(angle_tracker.get_value())
            ),
            buff=0,
            color=COLOR_VECTOR_B,
            stroke_width=6
        ))

        label_b = always_redraw(lambda: MathTex(r"\vec{b}", color=COLOR_VECTOR_B).next_to(
            vec_b.get_end(), UP if angle_tracker.get_value() > 0 else DOWN, buff=0.2
        ))

        # Angle arc
        angle_arc = always_redraw(lambda: Angle(
            vec_a, vec_b,
            radius=0.7,
            color=COLOR_ANGLE_ARC
        ) if angle_tracker.get_value() > 0.01 else VMobject())

        # Dot product value display
        dot_product_text = always_redraw(lambda: MathTex(
            r"\vec{a} \cdot \vec{b} = " + f"{9 * np.cos(angle_tracker.get_value()):.1f}",
            font_size=36,
            color=COLOR_RESULT
        ).to_corner(UL, buff=0.7).shift(DOWN * 1.2))

        angle_text = always_redraw(lambda: MathTex(
            r"\theta = " + f"{np.degrees(angle_tracker.get_value()):.0f}°",
            font_size=32,
            color=COLOR_ANGLE_ARC
        ).next_to(dot_product_text, DOWN, aligned_edge=LEFT, buff=0.3))

        self.add(vec_b, label_b, angle_arc, dot_product_text, angle_text)
        self.wait()

        # Rotate through different angles
        angles_to_show = [
            (0, "0° - Maximum positive (parallel)"),
            (PI / 4, "45° - Still positive"),
            (PI / 2, "90° - Zero (perpendicular)"),
            (3 * PI / 4, "135° - Negative"),
            (PI, "180° - Maximum negative (antiparallel)")
        ]

        for target_angle, description in angles_to_show:
            desc_text = Text(description, font_size=28, color=GREY).to_edge(DOWN, buff=0.5)
            self.play(
                angle_tracker.animate.set_value(target_angle),
                run_time=2
            )
            self.add(desc_text)
            self.wait(2)
            self.remove(desc_text)

        # Return to start
        self.play(angle_tracker.animate.set_value(0), run_time=2)
        self.wait(2)


# ==================== MAIN RENDERING INSTRUCTIONS ====================
if __name__ == "__main__":
    """
    To render these scenes, use the following commands:

    # Render all scenes in low quality for preview:
    manim -ql dot_product_manim.py

    # Render specific scene in high quality:
    manim -qh dot_product_manim.py Scene01_Introduction

    # Render all scenes in production quality:
    manim -qh dot_product_manim.py

    Scene List:
    1. Scene01_Introduction - Basic definitions
    2. Scene02_AlgebraicCalculation - Component-wise calculation
    3. Scene03_GeometricVisualization - Geometric interpretation with angles
    4. Scene04_Projections - Scalar and vector projections
    5. Scene05_Orthogonality - Perpendicular vectors
    6. Scene06_AngleCalculation - Finding angles between vectors
    7. Scene07_WorkApplication - Real-world physics application
    8. Scene08_Summary - Comprehensive summary
    9. Scene09_InteractiveAngle - Dynamic angle demonstration
    """
    pass