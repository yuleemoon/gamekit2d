"""Game 主类：窗口、主循环、事件分发、场景管理、对象工厂。

这是整个库的"总控"。用户通过 ``Game`` 一个对象完成几乎所有事情：
创建窗口、创建精灵 / 文本 / 按钮 / 粒子 / 音效、注册输入与碰撞回调、运行游戏。

渲染由可插拔的后端实现（``backend=``）：默认 ``"auto"`` 在 Windows 上
自动使用高性能 GDI 后端，其他平台回落 tkinter；也可显式指定 ``"tk"``。
"""

import sys
import time

from ..utils.color import to_color
from .keys import normalize


class Game:
    """一个 2D 游戏。

    :param title: 窗口标题
    :param width, height: 窗口尺寸（像素）
    :param fps: 目标帧率
    :param bg_color: 背景颜色（默认深色）
    :param resizable: 是否允许用户调整窗口大小
    :param backend: 渲染后端，``"auto"``（默认）/ ``"tk"`` / ``"gdi"``。
        ``"auto"`` = Windows 上用 GDI（快），其他平台用 tkinter。
    :param dirty: 脏矩形局部更新。``True`` 时不整屏清屏，只把上一帧精灵
        停留过的小矩形刷回背景色。适合"少量动态对象 + 静态背景"的场景
        （菜单、UI、少量移动元素）；动态精灵很多时反而比整屏清屏慢。
        仅 GDI 后端有效。
    """

    def __init__(self, title="GameKit", width=800, height=600, fps=60,
                 bg_color="#14141a", resizable=False, backend="auto",
                 dirty=False):
        self.title = title
        self.width = int(width)
        self.height = int(height)
        self.fps = max(1, int(fps))
        self.bg_color = to_color(bg_color)

        # ---- 渲染后端 ----
        from ..render.backend import TkRenderer, GdiRenderer, D2DRenderer, D3D11Renderer
        if backend == "auto":
            backend = "gdi" if sys.platform == "win32" else "tk"
        if backend == "gdi":
            self._renderer = GdiRenderer(self.width, self.height, title, self.bg_color)
        elif backend == "d2d":
            self._renderer = D2DRenderer(self.width, self.height, title, self.bg_color)
        elif backend == "d3d11":
            self._renderer = D3D11Renderer(self.width, self.height, title, self.bg_color)
        else:
            self._renderer = TkRenderer(self.width, self.height, title, self.bg_color,
                                        resizable=resizable)
        self.backend = self._renderer.__class__.__name__

        # ---- 时间 ----
        self._time = 0.0          # 累计运行时间（秒）
        self._dt = 1.0 / self.fps
        self._last = 0.0
        self._running = False
        self._closed = False

        # ---- 相机（世界坐标 -> 屏幕坐标的偏移）----
        # camera_x/camera_y 是世界坐标左上角对应屏幕 (0,0) 的位置。
        # 设置后所有绘制自动偏移，完全在屏幕外的精灵直接跳过不画。
        self.camera_x = 0
        self.camera_y = 0

        # ---- 脏矩形局部更新（仅 GDI 后端）----
        # _last_bboxes: id(obj) -> (l,t,r,b)，每个可绘制对象上一帧位置
        # _moved: 本帧需要在恢复阶段擦除旧像素的对象（位置变了 / 新出现）
        self._dirty = bool(dirty) and (self.backend == "GdiRenderer")
        self._last_bboxes = {}
        self._moved = {}
        self._dirty_first = True   # 第一帧必须全画（静态精灵首次入缓冲）

        # ---- 全局物理 ----
        self.gravity = 0.0        # 像素/秒^2，作用于 gravity_scale>0 的精灵

        # ---- 场景 ----
        self._scenes = []
        self._current_scene = None
        # 当前场景持有的对象列表（无场景时是 Game 自己的列表）
        self._sprites = []
        self._active_sprites = []  # only sprites with physics/update hooks
        self._gdi_sprites = []     # sprites drawn via GDI path (no C persistence)
        self._shapes = []
        self._texts = []
        self._ui_elements = []
        self._particles = []

        # ---- 回调注册表 ----
        self._update_handlers = []
        self._key_press_handlers = {}     # keysym -> [fn]
        self._key_release_handlers = {}
        self._key_hold_handlers = {}      # keysym -> [fn]（按住持续触发）
        self._mouse_handlers = {
            "click": [], "down": [], "up": [], "move": [], "wheel": [],
        }
        self._collide_handlers = []       # [(a, b, fn)]
        self._colliding_pairs = set()     # 上升沿检测（只触发一次）

        # ---- 定时器 ----
        self._timers = []

        # ---- 输入状态 ----
        self.keys_held = set()
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_buttons = set()
        # 上一帧输入快照，用于上升沿 / 下降沿检测
        self._prev_keys = set()
        self._prev_buttons = set()
        self._prev_mouse = (0, 0)

    # ==================================================================
    # 运行控制
    # ==================================================================
    def run(self):
        """启动游戏主循环（阻塞，直到窗口关闭或调用 stop）。"""
        if self._closed:
            raise RuntimeError("Game 已关闭，无法再次运行；请创建新的 Game 实例")
        self._running = True
        self._last = time.perf_counter()
        delay = int(1000.0 / self.fps)
        self._renderer.run_loop(self._tick, delay)
        self._closed = True
        self._renderer.close()

    def stop(self):
        """停止游戏。窗口会在循环退出后关闭。"""
        if self._closed:
            return
        self._running = False
        self._renderer.stop()

    @property
    def running(self):
        return self._running

    def set_fps(self, fps):
        """运行中调整目标帧率（等价于 pygame.time.Clock.tick 的效果）。"""
        self.fps = max(1, int(fps))
        return self

    # ---- 主循环 ----
    def _tick(self):
        if not self._running or self._closed:
            return
        now = time.perf_counter()
        self._dt = min(now - self._last, 0.05)   # 防止窗口拖动等造成超大 dt
        self._last = now
        self._time += self._dt

        self._dispatch_input()
        self._update()
        if not self._running or self._closed:
            return   # stop() 可能在 update 阶段被调用，此时不再渲染
        self._render()

    # ==================================================================
    # 更新与渲染
    # ==================================================================
    def _update(self):
        dt = self._dt
        self._process_timers()
        if self._closed or not self._running:
            return   # stop() 可能在定时器回调中被调用，此时停止一切后续更新

        scene = self._current_scene
        if scene is not None:
            scene.on_update(dt)

        # D2D fast path: skip physics for static sprites
        r = self._renderer
        d2d_fast = hasattr(r, "render_psprites")
        if d2d_fast:
            # Only iterate sprites that actually need per-frame updates
            for s in self._active_sprites:
                if s._removed:
                    continue
                s._physics_update(dt, self.gravity)
        else:
            for s in list(self._sprites):
                if not s._removed:
                    s._physics_update(dt, self.gravity)

        for sh in self._shapes:
            if not sh._removed:
                sh._physics_update(dt, self.gravity)

        for ps in self._particles:
            if not ps._removed:
                ps.update(dt)

        self._check_collisions()

        if self._closed or not self._running:
            return

        for fn in self._update_handlers:
            fn(dt)

        # 按住持续触发的按键回调
        for keysym in list(self.keys_held):
            for fn in self._key_hold_handlers.get(keysym, []):
                fn(dt)

    def _render(self):
        r = self._renderer
        ox, oy = int(self.camera_x), int(self.camera_y)

        # D2D/D3D fast path: skip Python sprite traversal, render C array directly.
        if hasattr(r, "render_psprites") and not self._dirty:
            r.begin_frame(clear=True, ox=ox, oy=oy)
            r.render_psprites()
            # Non-persistent sprites (circles / images / not-registered) still
            # need the GDI path. Persistent ones never enter this list.
            for s in self._gdi_sprites:
                if not s._removed and s.visible:
                    s._draw(r)
            for sh in self._shapes:
                if not sh._removed and sh.visible:
                    sh._draw(r)
            for t in self._texts:
                if not t._removed:
                    t._draw(r)
            for u in self._ui_elements:
                if not u._removed:
                    u._draw(r)
            for ps in self._particles:
                if not ps._removed:
                    ps._draw(r)
            r.end_frame()
            return

        if self._dirty:
            self._render_dirty(r, ox, oy)
        else:
            r.begin_frame(clear=True, ox=ox, oy=oy)
            self._draw_all(r)

        for t in list(self._texts):
            if not t._removed:
                t._draw(r)

        for u in list(self._ui_elements):
            if not u._removed:
                u._draw(r)

        for ps in list(self._particles):
            if not ps._removed:
                ps._draw(r)

        r.end_frame()

    def _collect_drawables(self):
        """收集当前帧需要绘制的精灵/图形，按 layer 排序。

        - camera 在原点 (0,0) 时跳过视口裁剪
        - 所有可见精灵同 layer 时跳过 sort（绝大多数游戏默认情况）
        """
        vx, vy = int(self.camera_x), int(self.camera_y)
        cam = (vx != 0 or vy != 0)
        vleft, vtop = vx, vy
        vright, vbottom = vx + self.width, vy + self.height
        drawables = []
        first_layer = None
        mixed = False
        for s in self._sprites:
            if s._removed or not s.visible:
                continue
            if cam and (s.right < vleft or s.left > vright
                        or s.bottom < vtop or s.top > vbottom):
                continue
            drawables.append((s.layer, s))
            if first_layer is None:
                first_layer = s.layer
            elif s.layer != first_layer:
                mixed = True
        for sh in self._shapes:
            if sh._removed or not sh.visible:
                continue
            drawables.append((sh.layer, sh))
            if sh.layer != first_layer:
                mixed = True
        if mixed:
            drawables.sort(key=lambda x: x[0])
        return drawables

    def _draw_all(self, r):
        """整屏清屏模式：画全部精灵/图形。"""
        # 快路径：camera 在原点时直接遍历，不建 list 不 sort
        if self.camera_x == 0 and self.camera_y == 0:
            for s in self._sprites:
                if not s._removed and s.visible:
                    s._draw(r)
            for sh in self._shapes:
                if not sh._removed and sh.visible:
                    sh._draw(r)
            return
        for _, obj in self._collect_drawables():
            obj._draw(r)

    @staticmethod
    def _bbox_intersects(l, t, r, b, rect):
        rl, rt, rr, rb = rect
        return not (r < rl or l > rr or b < rt or t > rb)

    def _render_dirty(self, r, ox=0, oy=0):
        """脏矩形模式：不清整屏，静态精灵只画一次，动态精灵旧位置用背景恢复。"""
        r.begin_frame(clear=False, ox=ox, oy=oy)
        dirty = list(self._moved.values())   # 上一帧动态精灵的旧位置
        if dirty:
            r.recover_background(dirty)

        vleft, vtop = ox, oy
        vright, vbottom = ox + self.width, oy + self.height
        def on_screen(s):
            return not (s.right < vleft or s.left > vright
                        or s.bottom < vtop or s.top > vbottom)

        statics = []
        dynamics = []
        seen = set()
        for s in self._sprites:
            if s._removed or not s.visible or not on_screen(s):
                continue
            if getattr(s, "static", False):
                statics.append((s.layer, s))
            else:
                dynamics.append((s.layer, s))

        if self._dirty_first:
            # 第一帧：所有精灵都要画进后台缓冲（包括静态的）
            to_draw = [(sh.layer, sh) for sh in self._shapes if not sh._removed and sh.visible]
            to_draw.extend(statics)
            to_draw.extend(dynamics)
            to_draw.sort(key=lambda x: x[0])
            for _, obj in to_draw:
                obj._draw(r)
                if hasattr(obj, "left"):
                    seen.add(id(obj))
            self._dirty_first = False
            # 记录所有动态精灵 bbox（静态精灵不进 _last_bboxes，
            # 它们位置不变，以后靠"与脏区相交才重画"管理）
            for _, s in dynamics:
                self._last_bboxes[id(s)] = (int(s.left), int(s.top),
                                            int(s.right), int(s.bottom))
            return

        # 后续帧：静态精灵只有 bbox 与脏区相交时才重画（被动态精灵压过）
        redraw_statics = []
        for layer, s in statics:
            sl = int(s.left); st = int(s.top); sr = int(s.right); sb = int(s.bottom)
            if any(self._bbox_intersects(sl, st, sr, sb, d) for d in dirty):
                redraw_statics.append((layer, s))

        to_draw = redraw_statics + dynamics
        # shapes 每帧重画（简单起见，不做静态优化）
        for sh in self._shapes:
            if not sh._removed and sh.visible:
                to_draw.append((sh.layer, sh))
        to_draw.sort(key=lambda x: x[0])

        self._moved = {}
        for _, obj in to_draw:
            obj._draw(r)
            if hasattr(obj, "left") and not getattr(obj, "static", False):
                bid = id(obj)
                seen.add(bid)
                nb = (int(obj.left), int(obj.top),
                      int(obj.right), int(obj.bottom))
                old = self._last_bboxes.get(bid)
                if old is not None and old != nb:
                    self._moved[bid] = old
                self._last_bboxes[bid] = nb
        # 清理已删除动态精灵的 bbox 记录
        for bid in [b for b in self._last_bboxes if b not in seen]:
            self._last_bboxes.pop(bid, None)

    # ==================================================================
    # 定时器
    # ==================================================================
    def after(self, seconds, fn):
        """延迟 ``seconds`` 秒后调用 ``fn()`` 一次。"""
        self._timers.append([self._time + seconds, fn, None])
        return fn

    def every(self, seconds, fn):
        """每隔 ``seconds`` 秒调用一次 ``fn()``，返回可取消的句柄。"""
        t = [self._time + seconds, fn, seconds]
        self._timers.append(t)
        return t

    def cancel_timer(self, timer):
        """取消一个由 ``every`` 返回的定时器。"""
        if timer in self._timers:
            self._timers.remove(timer)

    def _process_timers(self):
        now = self._time
        for t in list(self._timers):
            due, fn, interval = t
            if now >= due:
                fn()
                if interval:
                    t[0] = now + interval   # 周期任务，安排下一次
                else:
                    self._timers.remove(t)

    # ==================================================================
    # 对象工厂
    # ==================================================================
    def sprite(self, image=None, x=0, y=0, width=None, height=None,
               color=None, shape="rect", tag=None, layer=0, static=False):
        """创建并返回一个精灵。

        ``game.sprite("player.png", x=100, y=100)``
        ``game.sprite(color="red", x=200, y=200, width=40, height=40, shape="circle")``

        ``static=True`` 标记静态精灵：dirty 模式下只在第一帧绘制，
        之后不再重画（被移动精灵压过时会自动重画那一块）。
        """
        from ..sprites.sprite import Sprite
        s = Sprite(self, image=image, x=x, y=y, width=width, height=height,
                   color=color, shape=shape, tag=tag, layer=layer,
                   static=static)
        if s not in self._sprites:
            self._sprites.append(s)
        # D2D: register rectangle sprites to C layer immediately
        r = self._renderer
        if (hasattr(r, "register_sprite") and s._photo is None
                and s.shape == "rect" and s.color is not None):
            from ..render.backend import _rgb
            key = str(s.color)
            c = r._color_cache.get(key)
            if c is None:
                rr, gg, bb = _rgb(key)
                c = (rr / 255.0, gg / 255.0, bb / 255.0)
                r._color_cache[key] = c
            cr, cg, cb = c
            s._c_idx = r.register_sprite(
                float(s.left), float(s.top),
                float(s.width), float(s.height),
                cr, cg, cb, 1.0)
            s._last_dx = s.left
            s._last_dy = s.top
        # Track active sprites (those needing per-frame physics/update)
        self._activate_sprite(s)
        # GDI-path sprites (non-persistent: circles, images, not-registered)
        if not hasattr(s, "_c_idx"):
            self._gdi_sprites.append(s)
        return s

    def text(self, content="", x=0, y=0, size=20, color="white",
             font=None, anchor="center", bold=False, italic=False):
        """创建并返回一个文本对象。"""
        from ..ui.text import Text
        t = Text(self, content, x, y, size, color, font, anchor, bold, italic)
        if t not in self._texts:
            self._texts.append(t)
        return t

    def button(self, text="Button", x=0, y=0, width=140, height=44,
               color="#3a6ea5", hover_color="#4a88c9", text_color="white",
               font_size=18, on_click=None):
        """创建并返回一个按钮。"""
        from ..ui.widgets import Button
        b = Button(self, text, x, y, width, height, color, hover_color,
                   text_color, font_size, on_click)
        if b not in self._ui_elements:
            self._ui_elements.append(b)
        return b

    def progress_bar(self, x=0, y=0, width=240, height=20,
                     value=0.0, max_value=100.0, color="#4caf50", bg="#333333"):
        """创建并返回一个进度条。"""
        from ..ui.widgets import ProgressBar
        p = ProgressBar(self, x, y, width, height, value, max_value, color, bg)
        if p not in self._ui_elements:
            self._ui_elements.append(p)
        return p

    def sound(self, path, volume=1.0, loop=False):
        """加载一个 WAV 音效 / 音乐并返回 ``Sound`` 对象。"""
        from ..audio.sound import Sound
        return Sound(path, volume=volume, loop=loop)

    def music(self, path):
        """加载并循环播放一段背景音乐（WAV）。"""
        from ..audio.sound import Sound
        s = Sound(path, loop=True)
        return s

    def tilemap(self, rows, tile_size=32, tile_defs=None, x=0, y=0):
        """从字符串数组快速铺一张瓦片地图（打砖块 / 平台关卡常用）。

        ``rows`` 是字符串列表，每个字符代表一格：

        ::

            map_rows = [
                "##########",
                "#........#",
                "#..SS....#",
                "##########",
            ]
            game.tilemap(map_rows, tile_size=32,
                         tile_defs={"#": "#4488ff", "S": "#ff4444"})

        未在 ``tile_defs`` 里出现的字符（如 ``.``）视为空气，不绘制。
        生成的瓦片都是 ``static=True`` 精灵，配合 camera 只画屏幕内。
        返回创建的精灵列表。
        """
        created = []
        for row_idx, row in enumerate(rows):
            for col_idx, ch in enumerate(row):
                color = tile_defs.get(ch) if tile_defs else None
                if color is None:
                    continue
                s = self.sprite(color=color,
                                x=x + col_idx * tile_size + tile_size / 2,
                                y=y + row_idx * tile_size + tile_size / 2,
                                width=tile_size, height=tile_size,
                                static=True)
                created.append(s)
        return created

    def particles(self, x=0, y=0, count=30, speed=(50, 180),
                  life=(0.4, 1.5), size=(2, 6), colors=("red", "orange", "yellow"),
                  gravity=120.0, spread=360):
        """创建并返回一个粒子系统（可反复 ``burst()``）。"""
        from ..fx.particles import ParticleSystem
        ps = ParticleSystem(self, x, y, count, speed, life, size,
                            list(colors), gravity, spread)
        if ps not in self._particles:
            self._particles.append(ps)
        return ps

    def burst(self, x, y, count=30, **kwargs):
        """在 (x, y) 一次性爆发粒子，返回临时粒子系统。"""
        ps = self.particles(x=x, y=y, count=count, **kwargs)
        ps.burst()
        return ps

    # ---- 绘制原语（pygame.draw 的替代）----
    def line(self, x1=0, y1=0, x2=0, y2=0, color="white", width=2,
             layer=0, tag=None):
        """创建一条线段，返回可移动 / 可删除的 Line 对象。"""
        from ..fx.draw import Line
        shape = Line(self, x1, y1, x2, y2, color, width, layer, tag)
        self._add_shape(shape)
        return shape

    def polygon(self, points, color="white", outline=None, layer=0, tag=None):
        """按点列表创建多边形，返回 Polygon 对象。

        ``points`` 形如 ``[(x1, y1), (x2, y2), ...]``。
        """
        from ..fx.draw import Polygon
        shape = Polygon(self, points, color, outline, layer, tag)
        self._add_shape(shape)
        return shape

    def ellipse(self, x=0, y=0, width=40, height=40, color="white",
                outline=None, layer=0, tag=None):
        """创建椭圆 / 圆形（描边可选），返回 Ellipse 对象。"""
        from ..fx.draw import Ellipse
        shape = Ellipse(self, x, y, width, height, color, outline, layer, tag)
        self._add_shape(shape)
        return shape

    def arc(self, x=0, y=0, width=40, height=40, start=0, extent=90,
            color="white", width_px=2, layer=0, tag=None):
        """创建一段弧，返回 Arc 对象。

        ``start`` 与 ``extent`` 单位为度，0 度朝右，顺时针增加。
        """
        from ..fx.draw import Arc
        shape = Arc(self, x, y, width, height, start, extent, color,
                    width_px, layer, tag)
        self._add_shape(shape)
        return shape

    # ---- 对象移除 ----
    def _add_shape(self, shape):
        if shape not in self._shapes:
            self._shapes.append(shape)

    def _remove_shape(self, shape):
        if shape in self._shapes:
            self._shapes.remove(shape)
    def _activate_sprite(self, sprite):
        """把精灵加入每帧物理/更新遍历列表（幂等，O(1)）。"""
        if not getattr(sprite, "_in_active", False):
            self._active_sprites.append(sprite)
            sprite._in_active = True

    def _remove_sprite(self, sprite):
        if sprite in self._sprites:
            self._sprites.remove(sprite)
        try:
            self._gdi_sprites.remove(sprite)
        except ValueError:
            pass
        if getattr(sprite, "_in_active", False):
            sprite._in_active = False
            try:
                self._active_sprites.remove(sprite)
            except ValueError:
                pass

    def _remove_text(self, text):
        if text in self._texts:
            self._texts.remove(text)

    def _remove_ui(self, ui):
        if ui in self._ui_elements:
            self._ui_elements.remove(ui)

    def _remove_particles(self, ps):
        if ps in self._particles:
            self._particles.remove(ps)

    def clear(self):
        """清空当前场景（或全局）的全部对象。"""
        self._sprites.clear()
        self._shapes.clear()
        self._texts.clear()
        self._ui_elements.clear()
        self._particles.clear()

    # ==================================================================
    # 场景管理
    # ==================================================================
    def add_scene(self, scene):
        """注册一个场景，返回该场景。"""
        if scene.game is None:
            scene.game = self
        if scene not in self._scenes:
            self._scenes.append(scene)
        return scene

    def switch_scene(self, scene):
        """切换到指定场景。旧场景 ``on_exit``，新场景 ``on_enter``。"""
        if self._current_scene is not None:
            self._current_scene.on_exit()
        if scene.game is None:
            scene.game = self
        self._current_scene = scene
        self._sprites = scene.sprites
        self._shapes = scene.shapes
        self._texts = scene.texts
        self._ui_elements = scene.ui_elements
        self._particles = scene.particles
        # 碰撞回调绑定的是具体精灵/场景，切换场景后旧回调必然失效，统一清理。
        # 按键/鼠标/update 回调是全局性的，跨场景保留。
        self._collide_handlers = []
        self._colliding_pairs.clear()
        scene.on_enter(self)
        return scene

    @property
    def current_scene(self):
        return self._current_scene

    # ==================================================================
    # 事件注册（装饰器风格）
    # ==================================================================
    def on_update(self, fn):
        """注册每帧更新回调：``@game.on_update``，签名 ``fn(dt)``。"""
        self._update_handlers.append(fn)
        return fn

    def on_key(self, key):
        """按键按下时触发一次：``@game.on_key("SPACE")``。"""
        keysym = normalize(key)

        def deco(fn):
            self._key_press_handlers.setdefault(keysym, []).append(fn)
            return fn
        return deco

    # 别名：按下
    on_key_down = on_key

    def on_key_up(self, key):
        """按键抬起时触发一次。"""
        keysym = normalize(key)

        def deco(fn):
            self._key_release_handlers.setdefault(keysym, []).append(fn)
            return fn
        return deco

    def on_key_hold(self, key):
        """按住按键期间每帧触发：``fn(dt)``。"""
        keysym = normalize(key)

        def deco(fn):
            self._key_hold_handlers.setdefault(keysym, []).append(fn)
            return fn
        return deco

    def on_mouse_click(self, fn):
        """左键点击：``fn(x, y)``。"""
        self._mouse_handlers["click"].append(fn)
        return fn

    def on_mouse_down(self, fn):
        """任意鼠标按键按下：``fn(x, y, button)``。"""
        self._mouse_handlers["down"].append(fn)
        return fn

    def on_mouse_up(self, fn):
        """任意鼠标按键抬起：``fn(x, y, button)``。"""
        self._mouse_handlers["up"].append(fn)
        return fn

    def on_mouse_move(self, fn):
        """鼠标移动：``fn(x, y)``。"""
        self._mouse_handlers["move"].append(fn)
        return fn

    def on_mouse_wheel(self, fn):
        """鼠标滚轮：``fn(delta, x, y)``。"""
        self._mouse_handlers["wheel"].append(fn)
        return fn

    def on_collide(self, a, b):
        """两个对象碰撞时触发一次（进入碰撞才触发）。

        ``a`` / ``b`` 可以是：
        - 一个 Sprite 实例
        - 一个标签字符串（匹配所有带该标签的精灵）
        - 一个列表（任一匹配）

        ::

            @game.on_collide(player, "coin")
            def collect(p, c):
                c.remove()
        """
        def deco(fn):
            self._collide_handlers.append((a, b, fn))
            return fn
        return deco

    # ==================================================================
    # 输入事件分发（后端无关：从 renderer 的输入状态检测边沿）
    # ==================================================================
    def _dispatch_input(self):
        r = self._renderer

        # 鼠标位置
        self.mouse_x, self.mouse_y = r.mouse_pos()

        # 按键：按下 / 抬起（边沿检测）
        now_keys = set(r.keys_held)
        for k in now_keys - self._prev_keys:
            for fn in self._key_press_handlers.get(k, []):
                fn()
        for k in self._prev_keys - now_keys:
            for fn in self._key_release_handlers.get(k, []):
                fn()
        self._prev_keys = now_keys
        self.keys_held = now_keys

        # 鼠标按钮：down / up / click
        now_buttons = set(r.mouse_buttons)
        for b in now_buttons - self._prev_buttons:
            for fn in self._mouse_handlers["down"]:
                fn(self.mouse_x, self.mouse_y, b)
            if b == 1:
                for fn in self._mouse_handlers["click"]:
                    fn(self.mouse_x, self.mouse_y)
                for u in list(self._ui_elements):
                    if not u._removed and hasattr(u, "_handle_click"):
                        u._handle_click(self.mouse_x, self.mouse_y)
        for b in self._prev_buttons - now_buttons:
            for fn in self._mouse_handlers["up"]:
                fn(self.mouse_x, self.mouse_y, b)
        self._prev_buttons = now_buttons
        self.mouse_buttons = now_buttons

        # 鼠标移动（位置变化才触发）
        pos = (self.mouse_x, self.mouse_y)
        if pos != self._prev_mouse:
            for fn in self._mouse_handlers["move"]:
                fn(self.mouse_x, self.mouse_y)
            self._prev_mouse = pos

        # 滚轮（GDI 后端暂不产生滚轮事件）
        delta = getattr(r, "wheel_delta", 0)
        if delta:
            for fn in self._mouse_handlers["wheel"]:
                fn(delta, self.mouse_x, self.mouse_y)
            r.wheel_delta = 0

    # ==================================================================
    # 碰撞检测
    # ==================================================================
    def _match(self, spec):
        """把一个碰撞规格解析为精灵列表。"""
        from ..sprites.sprite import Sprite
        if isinstance(spec, Sprite):
            return [spec] if spec in self._sprites and not spec._removed else []
        if isinstance(spec, str):
            return [s for s in self._sprites
                    if not s._removed and s.solid and s.visible and s.has_tag(spec)]
        if isinstance(spec, (list, tuple)):
            result = []
            for part in spec:
                for s in self._match(part):
                    if s not in result:
                        result.append(s)
            return result
        return []

    def _check_collisions(self):
        current = set()
        for a_spec, b_spec, fn in self._collide_handlers:
            for sa in self._match(a_spec):
                for sb in self._match(b_spec):
                    if sa is sb or not sa.solid or not sb.solid:
                        continue
                    if sa.collides_with(sb):
                        key = (id(sa), id(sb))
                        current.add(key)
                        if key not in self._colliding_pairs:
                            fn(sa, sb)
        self._colliding_pairs = current

    # ==================================================================
    # 便捷查询
    # ==================================================================
    @property
    def sprites(self):
        """当前场景（或全局）的精灵列表（只读）。"""
        return list(self._sprites)

    @property
    def time(self):
        """累计运行秒数。"""
        return self._time

    @property
    def dt(self):
        """上一帧耗时（秒）。"""
        return self._dt

    def find(self, tag):
        """按标签查找当前场景中的所有精灵。"""
        return [s for s in self._sprites if not s._removed and s.has_tag(tag)]

    def is_key_down(self, key):
        """查询某个键当前是否被按住。"""
        return normalize(key) in self.keys_held
