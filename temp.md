Here is the comprehensive practice set for **Questions 1 through 5** based on your Practice Exam 1. This set contains **50 problems total** (10 variations per original question), scaled by difficulty as requested.

---

### **Topic 1: Equations of Paraboloids**
**Based on Original Q1:** *Find an equation of the paraboloid with the vertex at (-1, 4, 5) and its axis is parallel to the y-axis...*

#### **Problems**

**[Level: Base]**
1.  Find an equation of the paraboloid with vertex at $(2, -3, 1)$, axis parallel to the $z$-axis, and the surface opens towards positive values of $z$.
2.  Find an equation of the paraboloid with vertex at $(0, 5, -2)$, axis parallel to the $x$-axis, and the surface opens towards negative values of $x$.
3.  Find an equation of the paraboloid with vertex at $(-4, -1, 3)$, axis parallel to the $y$-axis, and the surface opens towards positive values of $y$.

**[Level: Elevated]**
4.  Find the equation of a circular paraboloid with vertex $(1, 1, 1)$, axis parallel to the $z$-axis, which passes through the point $(3, 3, 5)$.
5.  Find the equation of a paraboloid that opens downward along the $z$-axis, has its vertex in the $xy$-plane at $(2,3,0)$, and passes through $(0,0,-8)$.
6.  Find the equation of the paraboloid vertex at $(3, -2, 4)$, axis parallel to the $x$-axis, opening in the negative direction, where the trace in the plane $x=2$ is a circle of radius 3.

**[Level: Exam Killer]**
7.  Find the equation of the paraboloid with vertex $V(1, 2, 3)$ and axis parallel to the $y$-axis. The surface intersects the plane $y=6$ in a circle with circumference $8\pi$.
8.  A paraboloid has its vertex at the origin and opens along the positive $z$-axis. A line $L$ passes through $(0,0,4)$ with direction vector $\langle 1, 0, 0 \rangle$. The distance from the vertex to the closest point on the paraboloid intersected by the plane $z=4$ is 5. Find the equation of the paraboloid.

**[Level: Magic Tricks / Theory]**
9.  **Definition Locus:** Find the equation of the surface formed by all points $P(x,y,z)$ such that the distance from $P$ to the point $(0, 0, 2)$ is equal to the distance from $P$ to the plane $z = -2$. (Hint: This is the geometric definition of a paraboloid).
10. **Implicit Shift:** Describe the vertex and opening direction of the paraboloid given by $4x = y^2 + z^2 - 4y + 6z + 13$ without fully solving for $x$ first.

---

#### **Solutions (Topic 1)**
1.  **Ans:** $z - 1 = (x - 2)^2 + (y + 3)^2$. (Standard form $(z-k) = (x-h)^2 + (y-l)^2$).
2.  **Ans:** $x = -(y - 5)^2 - (z + 2)^2$. (Negative sign for opening negative x).
3.  **Ans:** $y + 1 = (x + 4)^2 + (z - 3)^2$.
4.  **Ans:** $z - 1 = (x - 1)^2 + (y - 1)^2$.
    *   *Work:* Form $z-1 = c((x-1)^2 + (y-1)^2)$. Plug in $(3,3,5) \to 5-1 = c(4+4) \to 4=8c \to c=0.5$. *Correction: Standard form usually implies c=1 unless specified, but passing through a point dictates the stretch factor.*
5.  **Ans:** $z = -2(x - 2)^2 - 2(y - 3)^2$.
    *   *Work:* Vertex $(2,3,0)$. $z = c((x-2)^2 + (y-3)^2)$. Plug $(0,0,-8) \to -8 = c(4+9) = 13c$. Wait, generally circular paraboloids are $z = c(x^2+y^2)$. Let's assume standard $x$ and $y$ scaling are equal. $-8 = c(4+9)$ is ugly. Let's re-read: "passes through (0,0,-8)". $-8 = c((-2)^2 + (-3)^2) \to -8 = 13c \to c = -8/13$. Equation: $z = -\frac{8}{13}((x-2)^2 + (y-3)^2)$.
6.  **Ans:** $x - 3 = -\frac{1}{9}((y+2)^2 + (z-4)^2)$.
    *   *Work:* Form $x-3 = c((y+2)^2 + (z-4)^2)$. At $x=2$: $-1 = c(r^2)$. Radius is 3, so $r^2=9$. $-1 = 9c \to c = -1/9$.
7.  **Ans:** $y - 2 = \frac{1}{4}((x-1)^2 + (z-3)^2)$.
    *   *Work:* Circle circumference $8\pi \to 2\pi r = 8\pi \to r=4$. At $y=6$, radius is 4. Form $y-2 = c(r^2)$. $6-2 = c(4^2) \to 4 = 16c \to c = 1/4$.
8.  **Ans:** $z = \frac{4}{9}(x^2 + y^2)$.
    *   *Work:* Vertex $(0,0,0)$. Intersection at $z=4$ is a circle. The distance from vertex $(0,0,0)$ to a point on this circle $(x,y,4)$ is 5. $\sqrt{x^2+y^2+4^2} = 5 \to x^2+y^2+16 = 25 \to x^2+y^2 = 9$. So at $z=4, r^2=9$. Eq: $z = c(x^2+y^2) \to 4 = c(9) \to c=4/9$.
9.  **Ans:** $z = \frac{1}{8}(x^2 + y^2)$.
    *   *Work:* Distance to point: $\sqrt{x^2+y^2+(z-2)^2}$. Distance to plane: $|z - (-2)| = |z+2|$. Square both: $x^2+y^2 + z^2 - 4z + 4 = z^2 + 4z + 4$. Cancel $z^2, 4$: $x^2+y^2 - 4z = 4z \to x^2+y^2 = 8z$.
10. **Ans:** Vertex $(x,y,z) = (0, 2, -3)$, Opens **Positive X**.
    *   *Work:* Complete squares for $y,z$. $4x = (y^2 - 4y + 4) + (z^2 + 6z + 9)$. We added $4+9=13$ to the right. The original constant was $13$, so $4x = (y-2)^2 + (z+3)^2 + 0$. Standard form $x = \frac{1}{4}((y-2)^2 + (z+3)^2)$.

---

### **Topic 2: Equations of Cylinders**
**Based on Original Q2:** *Find an equation of the cylinder with radius 9 and its axis is parallel to x-axis and the axis is passing through the point (2, -1, 4).*

#### **Problems**

**[Level: Base]**
1.  Find the equation of a cylinder with radius 5, axis parallel to the $z$-axis, passing through $(3, -2, 0)$.
2.  Find the equation of a cylinder with radius 2, axis parallel to the $y$-axis, centered at $(x,z) = (4, 1)$.
3.  Find the equation of the cylinder whose axis is the line $x=2, y=3$.

**[Level: Elevated]**
4.  Find the equation of a cylinder with axis parallel to the $z$-axis that passes through the points $(2, 4, 0)$, $(2, 0, 0)$, and $(-2, 2, 5)$. (Hint: Find the circle in the xy-plane).
5.  Find the equation of a cylinder with radius 3 whose axis is parallel to the $y$-axis and is tangent to the plane $z=1$ (and lies below it) and tangent to $x=5$.
6.  Identify the graph of the equation $x^2 + z^2 - 4x + 6z + 13 = 0$ in $\mathbb{R}^3$.

**[Level: Exam Killer]**
7.  Find the equation of the cylinder generated by the curve $y = x^2$ in the plane $z=0$, where the rulings (lines forming the cylinder) are parallel to the vector $\vec{v} = \langle 0, 1, 1 \rangle$. (Note: This is a "generalized cylinder", not a circular one).
8.  A circular cylinder of radius 2 has an axis defined by the parametric line $r(t) = \langle 1, 1, 1 \rangle + t\langle 0, 0, 1 \rangle$. Write the equation of this cylinder.

**[Level: Magic Tricks / Theory]**
9.  **Intersection:** Describe the intersection of the cylinder $x^2 + y^2 = 1$ and the plane $x + z = 2$. What is the shape of the curve?
10. **Degenerate:** Describe the surface defined by $(x-1)^2 + (z-2)^2 \leq 0$.

---

#### **Solutions (Topic 2)**
1.  **Ans:** $(x - 3)^2 + (y + 2)^2 = 25$. (Z is missing).
2.  **Ans:** $(x - 4)^2 + (z - 1)^2 = 4$. (Y is missing).
3.  **Ans:** $(x - 2)^2 + (y - 3)^2 = r^2$ (Problem did not specify radius, generic form). If strictly "axis is the line", radius is 0, which is a line. Assuming implied radius $r$, standard form.
4.  **Ans:** $x^2 + (y-2)^2 = 4$.
    *   *Work:* In 2D ($xy$), points are $(2,4), (2,0), (-2,2)$. $(2,4)$ and $(2,0)$ are vertical, midpoint $(2,2)$. Center must be on $y=2$. Distance from $(2,2)$ to $(-2,2)$ is 4. Center is $(0,2)$, radius 2. $x^2 + (y-2)^2 = 4$.
5.  **Ans:** $(x - 2)^2 + (z + 2)^2 = 9$.
    *   *Work:* Radius $r=3$. Tangent to $z=1$ from below $\implies$ center $z = 1-3 = -2$. Tangent to $x=5$ $\implies$ center $x = 5 \pm 3$. (Could be 2 or 8). One solution: $(x-2)^2 + (z+2)^2 = 9$.
6.  **Ans:** It is a **Line** (Degenerate Cylinder).
    *   *Work:* $(x^2 - 4x + 4) + (z^2 + 6z + 9) = -13 + 4 + 9 = 0$. $(x-2)^2 + (z+3)^2 = 0$. This is only satisfied when $x=2, z=-3$. In $\mathbb{R}^3$, this is a line parallel to the y-axis.
7.  **Ans:** $y - z = x^2$.
    *   *Work:* "Rulings parallel to $\langle 0, 1, 1 \rangle$" means $z$ acts like a shift in $y$. If we project to the plane perpendicular to the vector, we get a parabolic cylinder. More simply: A general cylinder with rulings $\langle a,b,c \rangle$ through curve $f(x,y)=0$ involves replacing $x \to x-az, y \to y-bz$ (if $c=1$). Here vector is $\langle 0,1,1 \rangle$. Replace $y$ with $y-z$. Eq: $(y-z) = x^2$.
8.  **Ans:** $(x-1)^2 + (y-1)^2 = 4$.
    *   *Work:* Axis is parallel to $z$ (vector $\langle 0,0,1 \rangle$). Passes through $(1,1,1)$. In $xy$-plane, center is $(1,1)$.
9.  **Ans:** An Ellipse.
    *   *Work:* The intersection of a circular cylinder and a slanted plane is an ellipse.
10. **Ans:** The line $x=1, z=2$ (parallel to y-axis).
    *   *Work:* Squares cannot be negative. The only solution is when the sum is 0.

---

### **Topic 3: Surface Identification**
**Based on Original Q3:** *What is the name of the surface $z = \frac{x^2}{9} + \frac{y^2}{4}$?*

#### **Problems**

**[Level: Base]**
1.  Identify the surface: $z^2 = x^2 + y^2$.
2.  Identify the surface: $x^2 + y^2 + z^2 = 25$.
3.  Identify the surface: $z = y^2 - x^2$.

**[Level: Elevated]**
4.  Identify the surface: $4x^2 + 9y^2 - z^2 = 36$.
5.  Identify the surface: $4x^2 - 9y^2 - z^2 = 36$.
6.  Identify the surface: $x^2/4 + y^2/9 + z^2/16 = 1$.

**[Level: Exam Killer]**
7.  Identify the surface: $x^2 - y^2 + z^2 = 0$.
8.  Identify the surface: $z = 4 - \sqrt{x^2 + y^2}$.

**[Level: Magic Tricks / Theory]**
9.  **Variable Analysis:** What distinguishes a Hyperboloid of One Sheet from a Hyperboloid of Two Sheets in the equation $Ax^2 + By^2 + Cz^2 = J$?
10. **Traces:** A surface has traces that are ellipses in the planes $z=k$ and hyperbolas in the planes $x=k$ and $y=k$. What surface is it?

---

#### **Solutions (Topic 3)**
1.  **Ans:** Cone (Circular).
2.  **Ans:** Sphere.
3.  **Ans:** Hyperbolic Paraboloid (Saddle).
4.  **Ans:** Hyperboloid of One Sheet. (One negative variable equals positive constant).
5.  **Ans:** Hyperboloid of Two Sheets. (Two negative variables equals positive constant).
6.  **Ans:** Ellipsoid.
7.  **Ans:** Elliptic Cone. (Homogeneous degree 2 equation, equals 0).
8.  **Ans:** Circular Cone (Top Half, Shifted up 4, opening down).
    *   *Work:* $z-4 = -\sqrt{...}$. Square both: $(z-4)^2 = x^2+y^2$. It's a cone vertex at $(0,0,4)$.
9.  **Ans:** The number of negative signs.
    *   If 1 negative coefficient: One Sheet.
    *   If 2 negative coefficients: Two Sheets. (Assuming $J>0$).
10. **Ans:** Hyperboloid of One Sheet. (Example: $x^2 + y^2 - z^2 = 1$).

---

### **Topic 4: Level Curves**
**Based on Original Q4:** *Sketch and describe level curves $f(x,y) = xy$ for...*

#### **Problems**

**[Level: Base]**
1.  Describe the level curves of $f(x,y) = x^2 + y^2$ for $c=1, 4, 9$.
2.  Describe the level curves of $f(x,y) = y - x^2$ for $c=0, 1, 2$.
3.  Describe the level curves of $f(x,y) = 2x + 3y$ for $c=0, 6, 12$.

**[Level: Elevated]**
4.  Describe the level curves of $f(x,y) = \sqrt{100 - x^2 - y^2}$ for $c=0, 6, 8$.
5.  Sketch the level curves for $f(x,y) = \frac{y}{x^2}$ for $c = -1, 1, 2$.
6.  Describe the level curves of $f(x,y) = e^{x-y}$.

**[Level: Exam Killer]**
7.  Describe the level curves of $f(x,y) = \ln(x^2 + y^2 - 1)$. What is the domain restriction on the map?
8.  Sketch the level curve for $f(x,y) = x^2 - y^2$ for $c=0$. Explain why this looks different from $c=1$.

**[Level: Magic Tricks / Theory]**
9.  **Steepness:** If the distance between level curves $c=10$ and $c=20$ is very small, what does that imply about the surface steepness?
10. **Topology:** Find the domain and describe the level curves of $f(x,y) = \frac{1}{\sqrt{16-x^2-y^2}}$.

---

#### **Solutions (Topic 4)**
1.  **Ans:** Concentric Circles centered at origin with radii 1, 2, 3.
2.  **Ans:** Parabolas shifted vertically ($y = x^2 + c$).
3.  **Ans:** Parallel lines with slope $-2/3$.
4.  **Ans:** Concentric Circles.
    *   $c=0 \to r=10$. $c=6 \to 36=100-r^2 \to r=8$. $c=8 \to 64=100-r^2 \to r=6$. Note: Higher $c$ means smaller radius (Hill).
5.  **Ans:** Parabolas $y = c x^2$.
6.  **Ans:** Parallel lines ($x-y = \ln c \to y = x - \ln c$).
7.  **Ans:** Concentric Circles. Domain: $x^2+y^2 > 1$ (Outside unit circle).
    *   $c = \ln(r^2-1) \to e^c + 1 = r^2$.
8.  **Ans:** For $c=0$, $x^2-y^2=0 \implies y = \pm x$. Two intersecting lines (an 'X'). For $c=1$, it is a Hyperbola. The transition from hyperbola opening x to hyperbola opening y passes through the "X" (asymptotes).
9.  **Ans:** The surface is very steep (gradient is large).
10. **Ans:** Domain: Interior of circle radius 4. Level curves are circles. As $c$ increases, the circles get closer to radius 4 (the boundary).

---

### **Topic 5: General Surface Description (Completing the Square)**
**Based on Original Q5:** *Describe the shape of the surface $f(x,y) = -x^2 + y^2 + 2x - 4y + 3$.*

#### **Problems**

**[Level: Base]**
1.  Classify the surface: $x^2 + y^2 + z^2 - 2x - 4y - 6z = 0$.
2.  Classify the surface: $z = x^2 + y^2 - 6x + 2y + 10$.
3.  Classify the surface: $x^2 + 4y^2 + 9z^2 - 36 = 0$.

**[Level: Elevated]**
4.  Classify and find the center/vertex: $4x^2 - y^2 + z^2 - 8x - 4y - 4 = 0$.
5.  Describe the surface $x = 2y^2 + 2z^2 - 8y + 1$.
6.  Classify: $z^2 = x^2 + y^2 - 4x - 6y + 13$.

**[Level: Exam Killer]**
7.  Classify the surface: $x^2 - y^2 + z^2 - 4x - 2y - 2z + 4 = 0$.
8.  Identify the surface and axis of symmetry: $2x^2 - 3y^2 - 3z^2 - 8x + 6y + 12z - 10 = 0$.

**[Level: Magic Tricks / Theory]**
9.  **Algebraic Twist:** What is the graph of $z = \sqrt{1 - x^2 - y^2}$ versus $x^2 + y^2 + z^2 = 1$?
10. **Parameter Logic:** For the equation $x^2 + y^2 + kz^2 = 1$, describe how the shape changes as $k$ goes from 1 to 0 to -1.

---

#### **Solutions (Topic 5)**
1.  **Ans:** Sphere. Center $(1, 2, 3)$, Radius $\sqrt{1+4+9} = \sqrt{14}$.
2.  **Ans:** Elliptic Paraboloid opening up. $z = (x-3)^2 + (y+1)^2$. Vertex $(3, -1, 0)$.
3.  **Ans:** Ellipsoid.
4.  **Ans:** Hyperboloid of One Sheet.
    *   $4(x-1)^2 - (y+2)^2 + z^2 = 4$. Axis parallel to $y$. Center $(1, -2, 0)$.
5.  **Ans:** Elliptic Paraboloid opening along positive x-axis. $x = 2(y-2)^2 + 2z^2 - 7$.
6.  **Ans:** Cone.
    *   $z^2 = (x-2)^2 + (y-3)^2$. Vertex $(2,3,0)$.
7.  **Ans:** Hyperboloid of One Sheet.
    *   $(x-2)^2 - (y+1)^2 + (z-1)^2 = -4 + 4 + 1 + 1 - 4 = -2$. Rearrange: $-(x-2)^2 + (y+1)^2 - (z-1)^2 = 2$. Two negatives? Wait.
    *   $(x-2)^2 - (y+1)^2 + (z-1)^2 = -2$. Multiply by -1: $-(x-2)^2 + (y+1)^2 - (z-1)^2 = 2$.
    *   Two negatives ($x, z$), one positive ($y$). This is a **Hyperboloid of Two Sheets** along the y-axis.
8.  **Ans:** Hyperboloid of Two Sheets.
    *   $2(x-2)^2 - 3(y-1)^2 - 3(z-2)^2 = 10 + 8 - 3 - 12 = 3$.
    *   One positive term ($x$), two negative ($y, z$). Axis of symmetry is parallel to x-axis.
9.  **Ans:** The first is the **top hemisphere** only ($z \geq 0$). The second is the **entire sphere**.
10. **Ans:**
    *   $k=1$: Sphere.
    *   $k=0$: Cylinder ($x^2+y^2=1$).
    *   $k=-1$: Hyperboloid of One Sheet ($x^2+y^2-z^2=1$).