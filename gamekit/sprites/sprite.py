"""精灵（Sprite）：游戏中可移动、可绘制、可碰撞的对象。"""

import math

from ..utils.color import to_color
from .image import load_image, scale_image, rotate_image, flip_image
from ..physics.collision import rect_collide, circle_collide


class Sprite:
    """游戏中的可见对象。

    :param image: 图像文件路径（PNG/GIF/BMP/PPM），可选
    :param x, y: 中心点坐标
    :param width, height: 尺寸（无图像时必须给出，或有默认值）
    :param color: 填充颜色（无图像时用颜色+形状绘制）
    :param shape: ``"rect"``（矩形）或 ``"circle"``（圆形），仅对纯色精灵生效
    :param tag: 标签（字符串或字符串列表），用于 ``on_collide`` 批量匹配
    :param layer: 绘制层级，数值越大越靠上层

    常用属性：``vx`` / ``vy``（速度，像素/秒）、``angle``（角度，度）、
    ``visible``、``gravity_scale``、``friction``、``bounce``。
    """

    # 赋值这些字段会自动把精灵加入 Game 的每帧物理更新列表
    # （即使在创建之后才赋值，如 ``player.vx = 100``）。
    _ACTIVE_FIELDS = frozenset(
        ("vx", "vy", "on_update", "gravity_scale", "friction",
         "bounce", "keep_on_screen"))

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name in Sprite._ACTIVE_FIELDS:
            self._ensure_active()

    def __init__(self, game, image=None, x=0, y=0, width=None, height=None,
                 color=None, shape="rect", tag=None, layer=0, static=False):
        self.game = game

        # ---- 位置与速度 ----
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0

        # ---- 外观 ----
        self.angle = 0.0          # 度
        self._scale = 1.0
        self.visible = True
        self.color = to_color(color)
        self.shape = shape if shape in ("rect", "circle") else "rect"
        self.layer = layer
        self.tag = tag
        # static=True：标记为静态精灵。dirty 模式下它只在第一帧绘制，
        # 之后只要没被动态精灵压过就不再重画（像素留在后台缓冲里）。
        self.static = bool(static)
        self._image_path = None
        self._photo = None
        self._flip_h = False
        self._flip_v = False

        # ---- 物理 ----
        self.gravity_scale = 0.0  # 受重力影响程度（0 = 不受重力）
        self.friction = 0.0       # 速度衰减系数（0 = 无摩擦）
        self.bounce = 0.0         # 撞到屏幕边缘的反弹系数（0 = 不反弹）
        self.keep_on_screen = False  # 撞到屏幕边缘停下（不越界）

        # ---- 生命周期与扩展点 ----
        self.solid = True         # 是否参与碰撞
        self._removed = False
        self.on_update = None     # 自定义每帧逻辑：fn(dt)
        self.on_draw = None       # 自定义绘制钩子：fn(canvas)
        self.animation = None     # Animation 对象（可选）

        # ---- 设置图像 / 尺寸 ----
        if image is not None:
            self.image = image
        if width is not None and height is not None:
            self.width = float(width)
            self.height = float(height)
        elif self._photo is not None:
            self.width = float(self._photo.width())
            self.height = float(self._photo.height())
        else:
            self.width = float(width) if width else 40.0
            self.height = float(height) if height else 40.0

    # ------------------------------------------------------------------
    # 图像属性
    # ------------------------------------------------------------------
    @property
    def image(self):
        return self._image_path

    @image.setter
    def image(self, path):
        self._image_path = path
        try:
            self._photo = load_image(path)
            if self._scale != 1.0:
                self._photo = scale_image(self._photo, self._scale)
            if self.angle:
                self._photo = rotate_image(self._photo, self.angle)
            if self._flip_h or self._flip_v:
                self._photo = flip_image(self._photo, self._flip_h, self._flip_v)
            if self._photo is not None:
                self.width = float(self._photo.width())
                self.height = float(self._photo.height())
        except Exception as exc:
            # 无 tkinter root（如 GDI 后端）或图像无法解码时的优雅降级：
            # 精灵保留位置 / 碰撞 / 逻辑，只是不绘制图像。
            self._photo = None
            if not getattr(self, "_warned_image", False):
                self._warned_image = True
                print("gamekit: 图像加载失败，精灵回退为不可见（GDI 后端的图像渲染将在后续版本支持）: %s" % (path,))

    @property
    def photo(self):
        """底层图像对象（tkinter PhotoImage），一般不需要直接使用。"""
        return self._photo

    @property
    def scale(self):
        """当前图像缩放倍率（只读，用 ``set_scale`` 修改）。"""
        return self._scale

    def set_image(self, path):
        """更换精灵图像。"""
        self.image = path
        return self

    def set_scale(self, factor):
        """设置图像缩放倍率。"""
        if factor <= 0:
            raise ValueError("缩放倍率必须大于 0")
        self._scale = factor
        if self._image_path and self._photo is not None:
            try:
                img = scale_image(load_image(self._image_path), factor)
                if self.angle:
                    img = rotate_image(img, self.angle)
                if self._flip_h or self._flip_v:
                    img = flip_image(img, self._flip_h, self._flip_v)
                self._photo = img
                self.width = float(self._photo.width())
                self.height = float(self._photo.height())
            except Exception:
                self._photo = None
        return self

    def set_angle(self, degrees):
        """设置图像旋转角度（度）。"""
        self.angle = degrees % 360
        if self._image_path:
            img = scale_image(load_image(self._image_path), self._scale)
            img = rotate_image(img, self.angle)
            if self._flip_h or self._flip_v:
                img = flip_image(img, self._flip_h, self._flip_v)
            self._photo = img
            self.width = float(self._photo.width())
            self.height = float(self._photo.height())
        return self

    def flip(self, horizontal=False, vertical=False):
        """水平 / 垂直翻转图像（等价于 pygame.transform.flip）。"""
        self._flip_h = bool(horizontal)
        self._flip_v = bool(vertical)
        if self._image_path:
            img = scale_image(load_image(self._image_path), self._scale)
            if self.angle:
                img = rotate_image(img, self.angle)
            if self._flip_h or self._flip_v:
                img = flip_image(img, self._flip_h, self._flip_v)
            self._photo = img
            self.width = float(self._photo.width())
            self.height = float(self._photo.height())
        return self

    def save_image(self, path):
        """把当前图像保存到文件（等价于 pygame.image.save）。

        支持扩展名：.ppm / .pgm / .gif / .bmp（tkinter 决定）。保存 PNG 不受支持。
        """
        if self._photo is None:
            raise ValueError("纯色精灵没有图像可保存；请先用图像创建精灵")
        self._photo.write(path)
        return self

    def set_color(self, color):
        """更换纯色精灵颜色。"""
        self.color = to_color(color)
        return self

    def play(self, frames, fps=10, loop=True):
        """播放帧动画。

        :param frames: 图像路径列表（按播放顺序）
        :param fps: 播放帧率
        :param loop: 是否循环
        :return: 创建的 Animation 对象
        """
        from .animation import Animation
        self.animation = Animation(frames, fps, loop)
        self.animation.start()
        if self.animation.frame is not None:
            self.image = self.animation.frame
        return self.animation

    def stop_animation(self):
        """停止当前动画（停留在当前帧）。"""
        if self.animation is not None:
            self.animation.stop()
        return self

    # ------------------------------------------------------------------
    # 移动
    # ------------------------------------------------------------------
    def move(self, dx=0, dy=0):
        """相对移动。"""
        self.x += dx
        self.y += dy
        # 位置可能已变化：确保进入每帧遍历（C 层位置同步）
        self.game._activate_sprite(self)
        return self

    def move_to(self, x, y):
        """移动到指定坐标。"""
        self.x = float(x)
        self.y = float(y)
        self.game._activate_sprite(self)
        return self

    def look_at(self, other):
        """让精灵朝向另一个精灵 / 点。返回并设置指向目标的角度（度）。"""
        tx = other.x if hasattr(other, "x") else other[0]
        ty = other.y if hasattr(other, "y") else other[1]
        self.angle = math.degrees(math.atan2(ty - self.y, tx - self.x))
        return self.angle

    # ------------------------------------------------------------------
    # 可见性与生命周期
    # ------------------------------------------------------------------
    def hide(self):
        self.visible = False
        return self

    def show(self):
        self.visible = True
        return self

    def remove(self):
        """从游戏中移除该精灵。"""
        if not self._removed:
            self._removed = True
            self.game._remove_sprite(self)
        return self

    def has_tag(self, tag):
        """判断是否拥有指定标签。"""
        if isinstance(self.tag, str):
            return self.tag == tag
        if isinstance(self.tag, (list, tuple)):
            return tag in self.tag
        return False

    # ------------------------------------------------------------------
    # 碰撞与几何
    # ------------------------------------------------------------------
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

    @property
    def radius(self):
        """圆形精灵的半径（取宽高较小者的一半）。"""
        return min(self.width, self.height) / 2

    def collides_with(self, other):
        """检测与另一个精灵是否碰撞（圆形对圆形走圆形检测，否则走矩形）。"""
        if self.shape == "circle" and other.shape == "circle":
            return circle_collide(self, other)
        return rect_collide(self, other)

    def contains(self, x, y):
        """判断点 (x, y) 是否在精灵内部。"""
        if self.shape == "circle":
            dx = x - self.x
            dy = y - self.y
            return dx * dx + dy * dy <= self.radius ** 2
        return self.left <= x <= self.right and self.top <= y <= self.bottom

    def distance_to(self, other):
        """到另一个精灵中心的距离。"""
        return math.hypot(self.x - other.x, self.y - other.y)

    def bounce_off(self, other, restitution=1.0):
        """与另一个精灵碰撞后按重叠方向反弹，并把自身推出重叠区。

        非常适合弹球类游戏（如打砖块）：它会根据重叠方向自动
        反转 ``vx`` 或 ``vy``，并修正位置避免卡进对方内部。
        """
        dx = self.x - other.x
        dy = self.y - other.y
        overlap_x = (self.width + other.width) / 2 - abs(dx)
        overlap_y = (self.height + other.height) / 2 - abs(dy)
        if overlap_x <= 0 or overlap_y <= 0:
            return
        if overlap_x < overlap_y:
            if dx != 0:
                self.vx = abs(self.vx) * restitution if dx > 0 else -abs(self.vx) * restitution
            self.x += (1 if dx > 0 else -1) * overlap_x
        else:
            if dy != 0:
                self.vy = abs(self.vy) * restitution if dy > 0 else -abs(self.vy) * restitution
            self.y += (1 if dy > 0 else -1) * overlap_y

    # ------------------------------------------------------------------
    # 物理（由 Game 每帧调用，一般不需要手动调用）
    # ------------------------------------------------------------------
    def _ensure_active(self):
        """若精灵需要每帧物理/更新，则确保它进入 Game 的遍历列表。"""
        if getattr(self, "_in_active", False):
            return
        g = self.game
        if g is None:
            return
        if (getattr(self, "vx", 0.0) or getattr(self, "vy", 0.0)
                or getattr(self, "on_update", None) is not None
                or getattr(self, "animation", None) is not None
                or getattr(self, "gravity_scale", 0.0)
                or getattr(self, "friction", 0.0)
                or getattr(self, "bounce", 0.0)
                or getattr(self, "keep_on_screen", False)):
            g._activate_sprite(self)

    def _physics_update(self, dt, gravity):
        if self.animation is not None:
            self.animation.update(dt)
            frame = self.animation.frame
            if frame is not None and frame != self._image_path:
                self.image = frame

        if self.gravity_scale:
            self.vy += gravity * self.gravity_scale * dt
        if self.friction:
            f = max(0.0, 1.0 - self.friction * dt)
            self.vx *= f
            self.vy *= f

        if self.vx or self.vy:
            self.x += self.vx * dt
            self.y += self.vy * dt

        if self.bounce:
            self._bounce_off_edges()
        elif self.keep_on_screen:
            self._clamp_to_screen()

        if self.on_update:
            self.on_update(dt)

        # Sync position to C layer if registered and sprite moved
        if hasattr(self, "_c_idx"):
            dx, dy = self.left, self.top
            if dx != self._last_dx or dy != self._last_dy:
                self.game._renderer.set_sprite_pos(self._c_idx,
                                                    float(dx), float(dy))
                self._last_dx = dx
                self._last_dy = dy

    def _bounce_off_edges(self):
        g = self.game
        half_w, half_h = self.width / 2, self.height / 2
        if self.x - half_w < 0:
            self.x = half_w
            self.vx = abs(self.vx) * self.bounce
        elif self.x + half_w > g.width:
            self.x = g.width - half_w
            self.vx = -abs(self.vx) * self.bounce
        if self.y - half_h < 0:
            self.y = half_h
            self.vy = abs(self.vy) * self.bounce
        elif self.y + half_h > g.height:
            self.y = g.height - half_h
            self.vy = -abs(self.vy) * self.bounce

    def _clamp_to_screen(self):
        g = self.game
        half_w, half_h = self.width / 2, self.height / 2
        if self.x - half_w < 0:
            self.x = half_w
            self.vx = 0
        elif self.x + half_w > g.width:
            self.x = g.width - half_w
            self.vx = 0
        if self.y - half_h < 0:
            self.y = half_h
            self.vy = 0
        elif self.y + half_h > g.height:
            self.y = g.height - half_h
            self.vy = 0

    # ------------------------------------------------------------------
    # 绘制（由 Game 每帧调用）
    # ------------------------------------------------------------------
    def _draw(self, r):
        if self._photo is not None:
            r.draw_image(self.x, self.y, self._photo)
        elif self.color is not None:
            if self.shape == "circle":
                rad = self.radius
                r.draw_oval(self.x - rad, self.y - rad,
                            self.x + rad, self.y + rad,
                            self.color)
            else:
                # D2D persistent sprite fast path: register once, update pos per-frame.
                if hasattr(r, "register_sprite"):
                    if not hasattr(self, "_c_idx"):
                        key = str(self.color)
                        c = r._color_cache.get(key)
                        if c is None:
                            from ..utils.color import to_color
                            rgb = to_color(self.color)
                            c = (rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0)
                            r._color_cache[key] = c
                        cr, cg, cb = c
                        self._c_idx = r.register_sprite(
                            float(self.left), float(self.top),
                            float(self.width), float(self.height),
                            cr, cg, cb, 1.0)
                        self._last_dx = self.left
                        self._last_dy = self.top
                    dx, dy = self.left, self.top
                    if dx != self._last_dx or dy != self._last_dy:
                        r.set_sprite_pos(self._c_idx, float(dx), float(dy))
                        self._last_dx = dx
                        self._last_dy = dy
                    return
                # C 加速快路径：矩形精灵缓存自己的 Surface DC，每帧直接 push
                if hasattr(r, "push_rect") and self.color is not None:
                    if not hasattr(self, "_rect_dc"):
                        self._rect_dc = None
                    if self._rect_dc is None:
                        self._rect_dc = r.get_rect_dc(
                            int(self.width), int(self.height), self.color)
                    if self._rect_dc is not None:
                        r.push_rect(self._rect_dc,
                                    int(self.left) - int(self.game.camera_x),
                                    int(self.top) - int(self.game.camera_y),
                                    int(self.width), int(self.height))
                        return
                r.draw_rect(self.left, self.top,
                            self.right, self.bottom,
                            self.color)
        if self.on_draw:
            # 钩子兼容：tk 后端传真实 canvas，GDI 后端传 renderer
            self.on_draw(getattr(r, "canvas", None) or r)

    def __repr__(self):
        return "Sprite(x=%.1f, y=%.1f, w=%.1f, h=%.1f)" % (self.x, self.y, self.width, self.height)
