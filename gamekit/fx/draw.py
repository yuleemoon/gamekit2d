"""Drawing primitives: lines, polygons, ellipses, arcs.

These fill the role of ``pygame.draw``. Like sprites they are managed
by the Game (movable via ``vx``/``vy``, layered, taggable, removable),
but they stay visual-only: they do not participate in collision checks.
Use sprites for anything that needs to collide.
"""

from ..utils.color import to_color


class Shape:
    """Base class for free-form shapes.

    Attributes mirror a sprite: ``x``/``y`` (reference point), ``vx``/``vy``,
    ``visible``, ``layer``, ``tag``, plus ``remove()``.
    """

    def __init__(self, game, x=0.0, y=0.0, vx=0.0, vy=0.0,
                 layer=0, tag=None, visible=True):
        self.game = game
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.visible = bool(visible)
        self.layer = layer
        self.tag = tag
        self.on_update = None
        self._removed = False

    # ---- movement ---------------------------------------------------
    def move(self, dx=0, dy=0):
        self.x += dx
        self.y += dy
        return self

    def move_to(self, x, y):
        self.x = float(x)
        self.y = float(y)
        return self

    # ---- lifecycle ---------------------------------------------------
    def hide(self):
        self.visible = False
        return self

    def show(self):
        self.visible = True
        return self

    def remove(self):
        if not self._removed:
            self._removed = True
            self.game._remove_shape(self)
        return self

    def has_tag(self, tag):
        if isinstance(self.tag, str):
            return self.tag == tag
        if isinstance(self.tag, (list, tuple)):
            return tag in self.tag
        return False

    # ---- physics (called by Game, usually you don't call this) -------
    def _physics_update(self, dt, gravity):
        if self.vx or self.vy:
            self.x += self.vx * dt
            self.y += self.vy * dt
        if self.on_update:
            self.on_update(dt)

    def _draw(self, canvas):  # pragma: no cover - overridden
        raise NotImplementedError

    def __repr__(self):
        return "%s(x=%.1f, y=%.1f)" % (type(self).__name__, self.x, self.y)


class Line(Shape):
    """A straight segment from (x1, y1) to (x2, y2)."""

    def __init__(self, game, x1=0, y1=0, x2=0, y2=0, color="white",
                 width=2, layer=0, tag=None):
        super().__init__(game, x=(x1 + x2) / 2.0, y=(y1 + y2) / 2.0,
                         layer=layer, tag=tag)
        self.x1, self.y1 = float(x1), float(y1)
        self.x2, self.y2 = float(x2), float(y2)
        self.color = to_color(color)
        self.width = max(1, int(width))

    def set_points(self, x1, y1, x2, y2):
        """Change the two endpoints and keep the centre in sync."""
        self.x1, self.y1 = float(x1), float(y1)
        self.x2, self.y2 = float(x2), float(y2)
        self.x = (self.x1 + self.x2) / 2.0
        self.y = (self.y1 + self.y2) / 2.0
        return self

    def _physics_update(self, dt, gravity):
        if self.vx or self.vy:
            self.x += self.vx * dt
            self.y += self.vy * dt
            dx, dy = self.x2 - self.x1, self.y2 - self.y1
            self.x1 = self.x - dx / 2.0
            self.y1 = self.y - dy / 2.0
            self.x2 = self.x + dx / 2.0
            self.y2 = self.y + dy / 2.0
        if self.on_update:
            self.on_update(dt)

    def _draw(self, r):
        if not self.visible:
            return
        r.draw_line(self.x1, self.y1, self.x2, self.y2,
                    self.color, self.width)


class Polygon(Shape):
    """A polygon defined by a list of (x, y) points."""

    def __init__(self, game, points, color="white", outline=None,
                 layer=0, tag=None):
        pts = [(float(px), float(py)) for px, py in points]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        super().__init__(game,
                         x=(min(xs) + max(xs)) / 2.0 if pts else 0.0,
                         y=(min(ys) + max(ys)) / 2.0 if pts else 0.0,
                         layer=layer, tag=tag)
        self.points = pts
        self.color = to_color(color)
        self.outline = to_color(outline)

    @property
    def left(self):
        return min(p[0] for p in self.points) if self.points else self.x

    @property
    def right(self):
        return max(p[0] for p in self.points) if self.points else self.x

    @property
    def top(self):
        return min(p[1] for p in self.points) if self.points else self.y

    @property
    def bottom(self):
        return max(p[1] for p in self.points) if self.points else self.y

    def _physics_update(self, dt, gravity):
        if self.vx or self.vy:
            dx, dy = self.vx * dt, self.vy * dt
            self.x += dx
            self.y += dy
            self.points = [(px + dx, py + dy) for px, py in self.points]
        if self.on_update:
            self.on_update(dt)

    def _draw(self, r):
        if not self.visible or not self.points:
            return
        r.draw_polygon(self.points, self.color, self.outline)


class Ellipse(Shape):
    """An ellipse (or circle) centred at (x, y)."""

    def __init__(self, game, x=0, y=0, width=40, height=40, color="white",
                 outline=None, layer=0, tag=None):
        super().__init__(game, x=x, y=y, layer=layer, tag=tag)
        self.width = float(width)
        self.height = float(height)
        self.color = to_color(color)
        self.outline = to_color(outline)

    @property
    def left(self):
        return self.x - self.width / 2

    @property
    def right(self):
        return self.x + self.width / 2

    @property
    def top(self):
        return self.y - self.height / 2

    @property
    def bottom(self):
        return self.y + self.height / 2

    def _draw(self, r):
        if not self.visible:
            return
        r.draw_oval(self.left, self.top, self.right, self.bottom,
                    self.color, self.outline)


class Arc(Shape):
    """An arc of an ellipse, from ``start`` to ``start + extent`` degrees.

    0 degrees points right, angles grow clockwise (canvas convention).
    """

    def __init__(self, game, x=0, y=0, width=40, height=40,
                 start=0, extent=90, color="white", width_px=2,
                 layer=0, tag=None):
        super().__init__(game, x=x, y=y, layer=layer, tag=tag)
        self.width = float(width)
        self.height = float(height)
        self.start = float(start)
        self.extent = float(extent)
        self.color = to_color(color)
        self.width_px = max(1, int(width_px))

    @property
    def left(self):
        return self.x - self.width / 2

    @property
    def right(self):
        return self.x + self.width / 2

    @property
    def top(self):
        return self.y - self.height / 2

    @property
    def bottom(self):
        return self.y + self.height / 2

    def _draw(self, r):
        if not self.visible:
            return
        r.draw_arc(self.left, self.top, self.right, self.bottom,
                   self.start, self.extent, self.color, self.width_px)
