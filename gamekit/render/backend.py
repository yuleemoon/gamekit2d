# gamekit.render.backend
# 渲染后端抽象：Renderer 接口 + 两个实现。
#
#   TkRenderer —— 默认后端，跨平台，基于 tkinter Canvas（保留模式）。
#   GdiRenderer —— 高性能后端，Windows 专用，基于自研 GDI 内核（立即模式）。
#
# Game 只依赖 Renderer 接口：创建窗口、跑循环、画矩形/圆/线/文字、
# 读输入状态。选哪个后端由 Game(backend=...) 决定，游戏代码不感知。
#
# GDI 后端为 Windows 原生窗口 + BitBlt 双缓冲，性能远高于 tkinter；
# 代价是仅 Windows 可用（其他平台自动回落 tkinter）。

import time

from ..utils.color import to_color

# ======================================================================
# 颜色工具：任意 gamekit 颜色字符串 -> (r, g, b)
# ======================================================================

# 常用颜色名 -> RGB（GDI 后端需要；tkinter 颜色名全集太大，这里覆盖常用）
_NAME_RGB = {
    "red": (255, 0, 0), "green": (0, 128, 0), "blue": (0, 0, 255),
    "yellow": (255, 255, 0), "gold": (255, 215, 0), "orange": (255, 165, 0),
    "purple": (128, 0, 128), "violet": (238, 130, 238), "pink": (255, 192, 203),
    "magenta": (255, 0, 255), "cyan": (0, 255, 255), "aqua": (0, 255, 255),
    "white": (255, 255, 255), "black": (0, 0, 0), "gray": (128, 128, 128),
    "grey": (128, 128, 128), "lime": (0, 255, 0), "brown": (165, 42, 42),
    "skyblue": (135, 206, 235), "navy": (0, 0, 128), "silver": (192, 192, 192),
    "maroon": (128, 0, 0), "olive": (128, 128, 0), "teal": (0, 128, 128),
    "indigo": (75, 0, 130), "coral": (255, 127, 80), "salmon": (250, 128, 114),
    "tomato": (255, 99, 71), "crimson": (220, 20, 60), "chocolate": (210, 105, 30),
    "beige": (245, 245, 220), "khaki": (240, 230, 140), "turquoise": (64, 224, 208),
}


def _rgb(color):
    """把颜色字符串转为 (r, g, b)。支持 '#rrggbb' 与常用颜色名。"""
    if not color:
        return (255, 255, 255)
    s = str(color).strip()
    if s.startswith("#") and len(s) == 7:
        return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16))
    if s.startswith("#") and len(s) == 4:
        return (int(s[1] * 2, 16), int(s[2] * 2, 16), int(s[3] * 2, 16))
    return _NAME_RGB.get(s.lower(), (255, 255, 255))


def _colorref(color):
    """颜色字符串 -> GDI COLORREF（0x00BBGGRR）。"""
    r, g, b = _rgb(color)
    return (b & 0xFF) | ((g & 0xFF) << 8) | ((r & 0xFF) << 16)


# ======================================================================
# Renderer 接口
# ======================================================================

class Renderer:
    """渲染后端接口。Game 与所有可绘制对象只调用这些方法。

    两个后端共享同一套绘制语义（坐标、颜色、锚点），但内部实现不同：
    tkinter 保留模式 vs GDI 立即模式。
    """

    # ---- 生命周期 ----
    def __init__(self, width, height, title, bg_color):
        raise NotImplementedError

    def run_loop(self, tick, frame_delay_ms):
        """启动阻塞式主循环。每帧调用 ``tick()``，两帧之间约等
        ``frame_delay_ms`` 毫秒。返回后循环结束。"""
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    # ---- 每帧 ----
    def pump(self):
        """拉取事件 / 输入状态（键、鼠标）。每帧开头调用。"""
        raise NotImplementedError

    def begin_frame(self, clear=True):
        """清屏并准备本帧绘制。``clear=False`` 时跳过全屏清屏
        （配合脏矩形局部恢复使用，仅 GDI 后端支持）。"""
        raise NotImplementedError

    def end_frame(self):
        """完成本帧并翻屏。"""
        raise NotImplementedError

    # ---- 输入状态（每帧 pump 后刷新）----
    @property
    def keys_held(self):
        return set()

    @property
    def mouse_x(self):
        return 0

    @property
    def mouse_y(self):
        return 0

    @property
    def mouse_buttons(self):
        return set()

    def is_key_down(self, keysym):
        return keysym in self.keys_held

    def mouse_pos(self):
        return (self.mouse_x, self.mouse_y)

    # ---- 绘制原语（对象层调用）----
    def draw_rect(self, x1, y1, x2, y2, color, outline=None, width=1):
        raise NotImplementedError

    def draw_oval(self, x1, y1, x2, y2, color, outline=None, width=1):
        raise NotImplementedError

    def draw_line(self, x1, y1, x2, y2, color, width=2):
        raise NotImplementedError

    def draw_polygon(self, points, color, outline=None):
        raise NotImplementedError

    def draw_arc(self, x1, y1, x2, y2, start, extent, color, width=2):
        raise NotImplementedError

    def draw_image(self, x, y, image):
        raise NotImplementedError

    def draw_text(self, x, y, content, color, font, size, weight, slant, anchor):
        raise NotImplementedError


# ======================================================================
# TkRenderer —— 默认后端（跨平台，tkinter）
# ======================================================================

class TkRenderer(Renderer):
    """基于 tkinter Canvas 的后端。保留模式：对象画到 canvas，由 Tk 管理。

    该后端为默认选项，任何平台都能跑。事件由 Tk 的 bind 驱动，
    通过 Canvas/root 的 bind 回调更新输入状态。
    """

    def __init__(self, width, height, title, bg_color, resizable=False):
        import tkinter as tk
        self.width = int(width)
        self.height = int(height)
        self.root = tk.Tk()
        self.root.title(title)
        self.root.resizable(bool(resizable), bool(resizable))
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height,
                                bg=bg_color, highlightthickness=0)
        self.canvas.pack()
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.root.focus_force()

        # 输入状态
        self._keys_held = set()
        self._mouse_buttons = set()
        self._mouse_x = 0
        self._mouse_y = 0
        self.wheel_delta = 0
        self._after_id = None
        self._running = False

        self._bind_events()

    def _bind_events(self):
        c = self.canvas
        c.bind("<Motion>", self._on_motion)
        c.bind("<ButtonPress>", self._on_down)
        c.bind("<ButtonRelease>", self._on_up)
        c.bind("<MouseWheel>", self._on_wheel)
        r = self.root
        r.bind("<KeyPress>", self._on_key_press)
        r.bind("<KeyRelease>", self._on_key_release)

    def _on_key_press(self, e):
        self._keys_held.add(e.keysym)

    def _on_key_release(self, e):
        self._keys_held.discard(e.keysym)

    def _on_motion(self, e):
        self._mouse_x, self._mouse_y = e.x, e.y

    def _on_down(self, e):
        self._mouse_buttons.add(e.num)

    def _on_up(self, e):
        self._mouse_buttons.discard(e.num)

    def _on_wheel(self, e):
        self.wheel_delta += int(e.delta)

    # ---- 生命周期 ----
    def run_loop(self, tick, frame_delay_ms):
        self._running = True
        self._tick = tick
        self._frame_delay_ms = max(1, int(frame_delay_ms))
        self._after_id = self.root.after(0, self._loop)
        self.root.mainloop()

    def _loop(self):
        if not self._running:
            return
        self._tick()
        if self._running:
            self._after_id = self.root.after(self._frame_delay_ms, self._loop)

    def stop(self):
        self._running = False
        if self._after_id:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        try:
            self.root.quit()
        except Exception:
            pass

    def close(self):
        self.stop()
        try:
            self.root.destroy()
        except Exception:
            pass

    # ---- 每帧 ----
    def pump(self):
        self.root.update()

    def begin_frame(self, clear=True, ox=0, oy=0):
        # tk 保留模式每帧必须全清；clear 参数仅为对齐接口。
        # ox/oy（camera 偏移）在 Tk 后端暂不应用，仅 GDI 后端支持 camera。
        self.canvas.delete("all")

    def end_frame(self):
        pass

    # ---- 输入 ----
    @property
    def keys_held(self):
        return self._keys_held

    @property
    def mouse_x(self):
        return self._mouse_x

    @property
    def mouse_y(self):
        return self._mouse_y

    @property
    def mouse_buttons(self):
        return self._mouse_buttons

    # ---- 绘制 ----
    def draw_rect(self, x1, y1, x2, y2, color, outline=None, width=1):
        self.canvas.create_rectangle(x1, y1, x2, y2,
                                     fill=color, outline=outline or "")

    def draw_oval(self, x1, y1, x2, y2, color, outline=None, width=1):
        self.canvas.create_oval(x1, y1, x2, y2,
                                fill=color, outline=outline or "")

    def draw_line(self, x1, y1, x2, y2, color, width=2):
        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=max(1, int(width)))

    def draw_polygon(self, points, color, outline=None):
        flat = []
        for px, py in points:
            flat.append(px)
            flat.append(py)
        self.canvas.create_polygon(*flat, fill=color,
                                   outline=outline or color)

    def draw_arc(self, x1, y1, x2, y2, start, extent, color, width=2):
        self.canvas.create_arc(x1, y1, x2, y2, start=start, extent=extent,
                               style="arc", outline=color, width=max(1, int(width)))

    def draw_image(self, x, y, image):
        self.canvas.create_image(x, y, image=image)

    def draw_text(self, x, y, content, color, font, size, weight, slant, anchor):
        self.canvas.create_text(
            x, y, text=content, fill=color,
            font=(font, size, weight, slant), anchor=anchor,
        )


# ======================================================================
# GdiRenderer —— 高性能后端（Windows 专用，自研 GDI 内核）
# ======================================================================

# 虚拟键码 -> gamekit keysym（与 tkinter keysym 一致）
_VK_TO_KEYSYM = {
    0x08: "BackSpace", 0x09: "Tab", 0x0D: "Return", 0x1B: "Escape",
    0x20: "space", 0x21: "Prior", 0x22: "Next", 0x23: "End", 0x24: "Home",
    0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",
    0x2E: "Delete", 0x10: "Shift_L", 0x11: "Control_L", 0x12: "Alt_L",
}
_VK_LIST = list(_VK_TO_KEYSYM.keys()) + list(range(0x30, 0x3A)) \
    + list(range(0x41, 0x5B)) + list(range(0x70, 0x7C))  # 0-9, A-Z, F1-F12


def _vk_to_keysym(vk):
    if vk in _VK_TO_KEYSYM:
        return _VK_TO_KEYSYM[vk]
    if 0x30 <= vk <= 0x39:
        return chr(0x30 + (vk - 0x30))
    if 0x41 <= vk <= 0x5A:
        return chr(0x61 + (vk - 0x41))
    if 0x70 <= vk <= 0x7B:
        return "F%d" % (vk - 0x70 + 1)
    return None


# 矩形 Surface 缓存上限：超过后回退直接 GDI 绘制，防 GDI 对象耗尽
_RECT_CACHE_MAX = 256

# 进程级共享的隐藏 tk root：PhotoImage 解码需要 Tk 默认 root
_shared_decode_root = None


class GdiRenderer(Renderer):
    """基于自研 GDI 内核的后端（立即模式）。

    - 渲染：每帧把对象画到后台 Surface（DIB），end_frame 一次性 BitBlt 翻屏
    - 输入：GetAsyncKeyState 轮询键盘 + GetCursorPos 轮询鼠标
    - 文字：GDI CreateFontW / TextOutW（带字体缓存）
    - 仅 Windows 可用；其他平台请用 TkRenderer
    """

    def __init__(self, width, height, title, bg_color):
        from .window import Window
        self.width = int(width)
        self.height = int(height)
        self._bg_rgb = _rgb(str(bg_color))
        self._ox = 0   # camera 偏移：所有 draw_* 的 x 世界坐标减这个
        self._oy = 0
        self._window = Window(self.width, self.height, title)
        self._screen = self._window.screen
        self._closed = False
        self._fonts = {}          # (family, size, bold, italic) -> HFONT
        self._image_cache = {}    # id(photo) -> Surface（图像精灵像素缓存）
        self._rect_cache = {}     # (w,h,color[,outline]) -> Surface（矩形精灵缓存）
        self._batch = []           # C 加速：本帧待 blit 的矩形
        try:
            from .. import _accel
            self._accel = _accel
        except ImportError:
            self._accel = None
        # 隐藏 tk root 是进程级共享单例：PhotoImage 解码需要 Tk 默认 root，
        # 但 Tcl 一次只能有一个解释器。多个 Game 复用同一个 root，
        # 不在每个后端关闭时 destroy（进程退出时一起回收）。
        global _shared_decode_root
        if _shared_decode_root is None:
            try:
                import tkinter as tk
                _shared_decode_root = tk.Tk()
                _shared_decode_root.withdraw()
            except Exception:
                _shared_decode_root = None
        self._decode_root = _shared_decode_root

        # 输入状态
        self._keys_held = set()
        self._mouse_buttons = set()
        self._mouse_x = 0
        self._mouse_y = 0
        self.wheel_delta = 0   # 本帧累计滚轮增量（Game 层读取后清零）

    # ---- 生命周期 ----
    def run_loop(self, tick, frame_delay_ms):
        delay = max(0.0, frame_delay_ms / 1000.0)
        while not self._closed:
            self.pump()
            if self._closed:
                break
            tick()
            if delay:
                time.sleep(delay)

    def stop(self):
        self._closed = True

    def close(self):
        self.stop()
        from . import win32
        for hfont in self._fonts.values():
            try:
                win32.gdi32.DeleteObject(hfont)
            except Exception:
                pass
        self._fonts.clear()
        for surf in self._image_cache.values():
            try:
                surf.close()
            except Exception:
                pass
        self._image_cache.clear()
        for surf in self._rect_cache.values():
            try:
                surf.close()
            except Exception:
                pass
        self._rect_cache.clear()
        self._window.close()
        # decode_root 是进程级共享单例，不在此处 destroy
        self._decode_root = None

    # ---- 每帧 ----
    def pump(self):
        if not self._window.poll_events():
            self._closed = True
        # 键盘轮询
        held = set()
        for vk in _VK_LIST:
            if self._window.is_key_down(vk):
                ks = _vk_to_keysym(vk)
                if ks:
                    held.add(ks)
        self._keys_held = held
        # 鼠标位置
        self._mouse_x, self._mouse_y = self._window.mouse_pos()
        # 鼠标按钮（VK_LBUTTON=1, VK_RBUTTON=2, VK_MBUTTON=4）
        buttons = set()
        if self._window.is_key_down(0x01):
            buttons.add(1)
        if self._window.is_key_down(0x04):
            buttons.add(2)
        if self._window.is_key_down(0x02):
            buttons.add(3)
        self._mouse_buttons = buttons
        # 滚轮（WM_MOUSEWHEEL 累积）
        self.wheel_delta = self._window.wheel_delta
        self._window.reset_wheel()

    def begin_frame(self, clear=True, ox=0, oy=0):
        # ox/oy 是 camera 偏移：世界坐标转屏幕坐标用
        self._ox = int(ox)
        self._oy = int(oy)
        self._batch = []
        if clear:
            self._screen.fill(self._bg_rgb)

    def recover_background(self, bboxes):
        """脏矩形局部恢复：用背景色填充一组包围盒 ``(x1,y1,x2,y2)``。

        与 ``begin_frame(clear=False)`` 配合：不整屏清屏，只把上一帧
        精灵停留过的小矩形刷回背景色。适合"少量动态对象 + 静态背景"。
        """
        from . import win32
        from ctypes import c_long
        if not bboxes:
            return
        hdc = self._select_brush(self._bg_rgb)
        stock = win32.gdi32.GetStockObject(win32.DC_BRUSH)
        for x1, y1, x2, y2 in bboxes:
            rect = (c_long * 4)(int(x1 - self._ox), int(y1 - self._oy),
                                int(x2 - self._ox), int(y2 - self._oy))
            win32.user32.FillRect(hdc, rect, stock)

    def end_frame(self, dirty_rects=None):
        # C 加速：批量执行本帧收集的矩形 blit
        if self._batch:
            if self._accel is not None:
                self._accel.batch_blit(self._screen.dc, self._batch)
            else:
                from . import win32
                for (hdc, x, y, w, h) in self._batch:
                    win32.gdi32.BitBlt(self._screen.dc, x, y, w, h,
                                       hdc, 0, 0, win32.SRCCOPY)
            self._batch = []
        self._window.present(dirty_rects)

    # ---- 输入 ----
    @property
    def keys_held(self):
        return self._keys_held

    @property
    def mouse_x(self):
        return self._mouse_x

    @property
    def mouse_y(self):
        return self._mouse_y

    @property
    def mouse_buttons(self):
        return self._mouse_buttons

    # ---- 绘制 ----
    def _hdc(self):
        return self._screen.dc

    def get_rect_dc(self, w, h, color):
        """返回矩形 Surface 的 DC（缓存命中或新建）。Sprite 每帧直接 push 用。"""
        key = (w, h, color, None)
        surf = self._rect_cache.get(key)
        if surf is not None:
            return surf._hdc
        if len(self._rect_cache) >= _RECT_CACHE_MAX:
            return None
        from .surface import Surface
        surf = Surface(w, h)
        surf.fill(_rgb(color))
        self._rect_cache[key] = surf
        return surf._hdc

    def push_rect(self, src_dc, x, y, w, h):
        """Sprite 直接把矩形 blit 请求推进批量队列。"""
        self._batch.append((src_dc, x, y, w, h))

    def _select_brush(self, color):
        """选择库存画刷并设置颜色，返回画刷句柄（无需删除）。"""
        from . import win32
        hdc = self._hdc()
        win32.gdi32.SelectObject(hdc, win32.gdi32.GetStockObject(win32.DC_BRUSH))
        win32.gdi32.SetDCBrushColor(hdc, _colorref(color))
        return hdc

    def _select_pen(self, color, width):
        """选择库存画笔并设置颜色。返回 hdc（笔是库存对象，无需删除）。"""
        from . import win32
        hdc = self._hdc()
        win32.gdi32.SelectObject(hdc, win32.gdi32.GetStockObject(win32.DC_PEN))
        win32.gdi32.SetDCPenColor(hdc, _colorref(color))
        return hdc

    def draw_rect(self, x1, y1, x2, y2, color, outline=None, width=1):
        # 矩形精灵优化（pygame 思路）：预渲染成小 Surface，每帧一次 BitBlt。
        # 同尺寸同色的矩形共享同一块像素缓存，避免每帧重复 GDI 绘制。
        # 缓存有上限（_RECT_CACHE_MAX）：颜色/尺寸组合太多（如全异色大场景）
        # 时回退直接 FillRect，防止 GDI 对象（DC+DIB）耗尽。
        w = int(round(x2 - x1))
        h = int(round(y2 - y1))
        if w <= 0 or h <= 0:
            return
        oc = str(outline) if outline else None
        key = (w, h, color, oc)
        x1s, y1s = int(x1) - self._ox, int(y1) - self._oy
        surf = self._rect_cache.get(key)
        if surf is not None:
            # C 加速：收集 blit 请求，帧末批量执行
            self._batch.append((surf._hdc, x1s, y1s, w, h))
            return
        if len(self._rect_cache) >= _RECT_CACHE_MAX:
            self._draw_rect_direct(x1, y1, x2, y2, color, oc, width)
            return
        from .surface import Surface
        surf = Surface(w, h)
        surf.fill(_rgb(color))
        if oc and oc.lower() not in ("", "none"):
            self._paint_border(surf, oc, width)
        self._rect_cache[key] = surf
        surf.blit(self._screen.dc, x1s, y1s)

    def _draw_rect_direct(self, x1, y1, x2, y2, color, outline, width):
        """无缓存回退：直接 GDI FillRect（+ 边框线）。"""
        from . import win32
        from ctypes import c_long
        x1 -= self._ox; x2 -= self._ox
        y1 -= self._oy; y2 -= self._oy
        hdc = self._select_brush(color)
        rect = (c_long * 4)(int(x1), int(y1), int(x2), int(y2))
        win32.user32.FillRect(hdc, rect, win32.gdi32.GetStockObject(win32.DC_BRUSH))
        if outline and outline.lower() not in ("", "none"):
            self.draw_line(x1, y1, x2, y1, outline, width)
            self.draw_line(x2, y1, x2, y2, outline, width)
            self.draw_line(x2, y2, x1, y2, outline, width)
            self.draw_line(x1, y2, x1, y1, outline, width)

    def _paint_border(self, surf, color, width):
        """在矩形 Surface 上描边（一次性，进缓存）。"""
        from . import win32
        w, h = surf.width, surf.height
        hdc = surf.dc
        win32.gdi32.SelectObject(hdc, win32.gdi32.GetStockObject(win32.DC_PEN))
        win32.gdi32.SetDCPenColor(hdc, _colorref(color))
        lw = max(1, int(width))
        win32.gdi32.MoveToEx(hdc, 0, 0, None)
        win32.gdi32.LineTo(hdc, w - 1, 0)
        win32.gdi32.LineTo(hdc, w - 1, h - 1)
        win32.gdi32.LineTo(hdc, 0, h - 1)
        win32.gdi32.LineTo(hdc, 0, 0)

    def draw_oval(self, x1, y1, x2, y2, color, outline=None, width=1):
        from . import win32
        x1 -= self._ox; x2 -= self._ox
        y1 -= self._oy; y2 -= self._oy
        hdc = self._select_brush(color)
        # 椭圆描边用同色，避免默认黑边
        pen_color = outline or color
        hdc = self._select_pen(pen_color, width)
        win32.gdi32.Ellipse(hdc, int(x1), int(y1), int(x2), int(y2))

    def draw_line(self, x1, y1, x2, y2, color, width=2):
        from . import win32
        hdc = self._select_pen(color, width)
        win32.gdi32.MoveToEx(hdc, int(x1 - self._ox), int(y1 - self._oy), None)
        win32.gdi32.LineTo(hdc, int(x2 - self._ox), int(y2 - self._oy))

    def draw_polygon(self, points, color, outline=None):
        from . import win32
        from ctypes import c_long
        if not points:
            return
        pts = [(int(x - self._ox), int(y - self._oy)) for x, y in points]
        hdc = self._select_brush(color)
        hdc = self._select_pen(outline or color, 1)
        arr = (c_long * (len(pts) * 2))()
        for i, (px, py) in enumerate(pts):
            arr[i * 2] = px
            arr[i * 2 + 1] = py
        win32.gdi32.Polygon(hdc, arr, len(pts))

    def draw_arc(self, x1, y1, x2, y2, start, extent, color, width=2):
        from . import win32
        import math
        x1 -= self._ox; x2 -= self._ox
        y1 -= self._oy; y2 -= self._oy
        hdc = self._select_pen(color, width)
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        rx = max(0.5, (x2 - x1) / 2.0)
        ry = max(0.5, (y2 - y1) / 2.0)
        # GDI Arc 角度：0 度向右，逆时针为正；canvas 是顺时针。换算。
        a0 = math.radians(-start)
        a1 = math.radians(-(start + extent))
        x0 = int(cx + rx * math.cos(a0))
        y0 = int(cy + ry * math.sin(a0))
        x1p = int(cx + rx * math.cos(a1))
        y1p = int(cy + ry * math.sin(a1))
        win32.gdi32.Arc(hdc, int(x1), int(y1), int(x2), int(y2),
                        x0, y0, x1p, y1p)

    def draw_image(self, x, y, image):
        # 图像精灵桥：tkinter PhotoImage -> Surface 像素缓存 -> alpha blit。
        # 首次遇到某张图时做一次像素转换（Python 逐像素，对小图可接受），
        # 之后每帧直接整块位块传送，不再走矢量重绘。
        if image is None:
            return
        if not self._decode_root:
            return
        surf = self._image_cache.get(id(image))
        if surf is None:
            from .surface import Surface
            w, h = image.width(), image.height()
            if w <= 0 or h <= 0:
                return
            surf = Surface(w, h)
            has_trans = hasattr(image, "transparency_get")
            for py in range(h):
                for px in range(w):
                    r, g, b = image.get(px, py)
                    a = 0 if (has_trans and image.transparency_get(px, py)) else 255
                    surf.set_at(px, py, (r, g, b, a))
            self._image_cache[id(image)] = surf
        # canvas.create_image 以 (x, y) 为中心。
        # AlphaBlend 对 top-down DIB 源不工作（实测），这里用软件 alpha 合成：
        # 直接读源 Surface 的 uint32 像素并写入目标 DIB 内存。
        # 精灵图多为 0/255 alpha（PNG 透明背景），快；有半透明时按比例混合。
        from . import win32
        src = surf._buf
        dst = self._screen._buf
        sw, sh = surf.width, surf.height
        ox = int(x - self._ox - sw / 2)
        oy = int(y - self._oy - sh / 2)
        W, H = self.width, self.height
        for py in range(sh):
            dy = oy + py
            if dy < 0 or dy >= H:
                continue
            row = dy * W
            srow = py * sw
            for px in range(sw):
                dx = ox + px
                if dx < 0 or dx >= W:
                    continue
                v = src[srow + px]
                a = (v >> 24) & 0xFF
                if a == 0:
                    continue
                if a == 255:
                    dst[row + dx] = v
                else:
                    ov = dst[row + dx]
                    # 预乘合成（SRC_OVER）
                    ia = 255 - a
                    nb = ((v & 0xFF) * a + (ov & 0xFF) * ia) // 255
                    ng = (((v >> 8) & 0xFF) * a + ((ov >> 8) & 0xFF) * ia) // 255
                    nr = (((v >> 16) & 0xFF) * a + ((ov >> 16) & 0xFF) * ia) // 255
                    dst[row + dx] = (nb & 0xFF) | ((ng & 0xFF) << 8) | ((nr & 0xFF) << 16) | 0xFF000000

    # ---- 文字 ----
    def _get_font(self, family, size, bold, slant):
        from . import win32
        key = (family, int(size), bool(bold), bool(slant))
        hfont = self._fonts.get(key)
        if hfont:
            return hfont
        weight = win32.FW_BOLD if bold else win32.FW_NORMAL
        hfont = win32.gdi32.CreateFontW(
            -int(size), 0, 0, 0, weight,
            1 if slant else 0, 0, 0,
            win32.DEFAULT_CHARSET,
            win32.OUT_DEFAULT_PRECIS,
            win32.CLIP_DEFAULT_PRECIS,
            win32.DEFAULT_QUALITY,
            win32.DEFAULT_PITCH | win32.FF_DONTCARE,
            family or "Microsoft YaHei",
        )
        if not hfont:
            hfont = win32.gdi32.CreateFontW(-int(size), 0, 0, 0, weight,
                                            0, 0, 0, win32.DEFAULT_CHARSET,
                                            0, 0, 0, 0, None)
        self._fonts[key] = hfont
        return hfont

    def draw_text(self, x, y, content, color, font, size, weight, slant, anchor):
        from . import win32
        from ctypes import byref
        text = str(content)
        hdc = self._hdc()
        hfont = self._get_font(font, size, weight == "bold", slant == "italic")
        win32.gdi32.SelectObject(hdc, hfont)
        win32.gdi32.SetTextColor(hdc, _colorref(color))
        win32.gdi32.SetBkMode(hdc, win32.TRANSPARENT)
        # 文本尺寸（用于锚点对齐）
        extent = win32.SIZE()
        if text:
            win32.gdi32.GetTextExtentPoint32W(hdc, text, len(text), byref(extent))
        w, h = extent.cx, extent.cy
        ax, ay = 0, 0
        if anchor in ("center", "n", "s"):
            ax = -w // 2
        elif anchor in ("ne", "e", "se"):
            ax = -w
        if anchor in ("w", "center", "e"):
            ay = -h // 2
        elif anchor in ("sw", "s", "se"):
            ay = -h
        win32.gdi32.TextOutW(hdc, int(x - self._ox) + ax, int(y - self._oy) + ay,
                             text, len(text))



# ======================================================================
# D2DRenderer —— Direct2D GPU 加速后端
# ======================================================================

class D2DRenderer(GdiRenderer):
    """基于 Direct2D 的 GPU 加速后端。

    - 渲染：GPU 硬件加速 FillRectangle（比 GDI BitBlt 快数倍）
    - 窗口：复用 GdiRenderer 的 Win32 窗口
    - 输入：复用 GdiRenderer 的 GetAsyncKeyState 轮询
    - 仅 Windows + Python 3.13（需要 _d2d.pyd）
    """

    def __init__(self, width, height, title, bg_color):
        super().__init__(width, height, title, bg_color)
        try:
            from .. import _d2d
        except ImportError:
            raise RuntimeError(
                "Direct2D backend requires _d2d.pyd (Python 3.13 on Windows). "
                "Use backend='gdi' or 'tk' instead.")
        self._d2d = _d2d
        self._d2d.init(self._window._hwnd)
        r, g, b = _rgb(bg_color)
        self._bg = (r / 255.0, g / 255.0, b / 255.0)
        self._color_cache = {}
        import array
        self._batch = array.array('f')

    def begin_frame(self, clear=True, ox=0, oy=0):
        self._ox = int(ox)
        self._oy = int(oy)
        self._d2d.clear_batch()
        if clear:
            self._d2d.begin(self._bg[0], self._bg[1], self._bg[2], 1.0)

    def end_frame(self, dirty_rects=None):
        self._d2d.render_batch()
        self._d2d.render_psprites()
        self._d2d.end()

    def draw_rect(self, x1, y1, x2, y2, color, outline=None, width=1):
        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            return
        key = str(color)
        c = self._color_cache.get(key)
        if c is None:
            r, g, b = _rgb(key)
            c = (r / 255.0, g / 255.0, b / 255.0)
            self._color_cache[key] = c
        cr, cg, cb = c
        self._d2d.push_rect(
            float(x1 - self._ox), float(y1 - self._oy),
            float(w), float(h), cr, cg, cb, 1.0)

    def push_rect(self, src_dc, x, y, w, h):
        # D2D: push_rect is not used (get_rect_dc returns None).
        pass

    def get_rect_dc(self, w, h, color):
        # Disable GDI DC cache: return None so Sprite falls through to draw_rect.
        return None

    def draw_text(self, x, y, content, color, font, size, weight, slant, anchor):
        # Fallback: use GDI TextOutW on window DC after D2D present.
        # D2D doesn't do text natively without DirectWrite; GDI overlay is fast enough.
        import ctypes
        from . import win32
        key = (font, size, weight, slant)
        hfont = self._fonts.get(key)
        if hfont is None:
            hfont = self._get_font(font, size, weight == "bold", slant == "italic")
            self._fonts[key] = hfont
        hdc = self._window._dc
        old = win32.gdi32.SelectObject(hdc, hfont)
        r, g, b = _rgb(str(color))
        win32.gdi32.SetTextColor(hdc, r | (g << 8) | (b << 16))
        win32.gdi32.SetBkMode(hdc, 1)  # TRANSPARENT
        text = str(content)
        # Measure text for anchor
        extent = win32.SIZE()
        win32.gdi32.GetTextExtentPoint32W(hdc, text, len(text),
                                            ctypes.byref(extent))
        tw, th = extent.cx, extent.cy
        ax, ay = 0, 0
        if anchor in ("n", "nw", "sw"):
            ax = 0
        elif anchor in ("ne", "e", "se"):
            ax = -tw
        else:
            ax = -tw // 2
        if anchor in ("nw", "n", "ne"):
            ay = 0
        elif anchor in ("sw", "s", "se"):
            ay = -th
        else:
            ay = -th // 2
        win32.gdi32.TextOutW(hdc,
                             int(x - self._ox) + ax,
                             int(y - self._oy) + ay,
                             text, len(text))
        win32.gdi32.SelectObject(hdc, old)

    def close(self):
        try:
            self._d2d.shutdown()
        except Exception:
            pass
        super().close()

    def draw_oval(self, x1, y1, x2, y2, color, outline=None, width=1):
        cx = (x1 + x2) / 2.0 - self._ox
        cy = (y1 + y2) / 2.0 - self._oy
        rx = (x2 - x1) / 2.0
        ry = (y2 - y1) / 2.0
        key = str(color)
        c = self._color_cache.get(key)
        if c is None:
            r, g, b = _rgb(key)
            c = (r / 255.0, g / 255.0, b / 255.0)
            self._color_cache[key] = c
        cr, cg, cb = c
        self._d2d.fill_ellipse(cx, cy, rx, ry, cr, cg, cb, 1.0)

    def draw_line(self, x1, y1, x2, y2, color, width=2):
        key = str(color)
        c = self._color_cache.get(key)
        if c is None:
            r, g, b = _rgb(key)
            c = (r / 255.0, g / 255.0, b / 255.0)
            self._color_cache[key] = c
        cr, cg, cb = c
        self._d2d.draw_line(
            float(x1 - self._ox), float(y1 - self._oy),
            float(x2 - self._ox), float(y2 - self._oy),
            cr, cg, cb, 1.0, float(width))

    def draw_polygon(self, points, color, outline=None):
        key = str(color)
        c = self._color_cache.get(key)
        if c is None:
            r, g, b = _rgb(key)
            c = (r / 255.0, g / 255.0, b / 255.0)
            self._color_cache[key] = c
        cr, cg, cb = c
        # points is list of (x,y); flatten to [x1,y1,x2,y2,...] with camera offset
        flat = []
        for p in points:
            flat.append(float(p[0] - self._ox))
            flat.append(float(p[1] - self._oy))
        self._d2d.fill_polygon(flat, cr, cg, cb, 1.0)

    def draw_arc(self, x1, y1, x2, y2, start, extent, color, width=2):
        key = str(color)
        c = self._color_cache.get(key)
        if c is None:
            r, g, b = _rgb(key)
            c = (r / 255.0, g / 255.0, b / 255.0)
            self._color_cache[key] = c
        cr, cg, cb = c
        self._d2d.fill_arc(
            float(x1 - self._ox), float(y1 - self._oy),
            float(x2 - self._ox), float(y2 - self._oy),
            float(start), float(extent),
            cr, cg, cb, 1.0)


class D3D11Renderer(GdiRenderer):
    """D3D11 GPU renderer: vertex buffer batching, one DrawIndexed per frame."""

    def __init__(self, width, height, title, bg_color):
        GdiRenderer.__init__(self, width, height, title, bg_color)
        import array
        try:
            from .. import _d3d11
            self._d3d = _d3d11
        except ImportError:
            raise RuntimeError("D3D11 extension not available")
        self._d3d.init(self._window._hwnd)
        r, g, b = _rgb(bg_color)
        self._bg_f = (r / 255.0, g / 255.0, b / 255.0)
        self._buf = array.array('f')
        self._color_cache = {}

    def begin_frame(self, clear=True, ox=0, oy=0):
        import array
        self._ox = int(ox)
        self._oy = int(oy)
        self._buf = array.array('f')
        self._gdi_hdc = None   # lazily acquired DXGI surface DC (GDI overlay)
        if clear:
            self._d3d.begin(self._bg_f[0], self._bg_f[1], self._bg_f[2], 1.0)

    def _hdc(self):
        """GDI 图元（文字/圆形/线条等）画到 DXGI back buffer 的 GDI DC，
        这样它们和 GPU 精灵在同一层，Present 后都可见。"""
        if self._gdi_hdc is None:
            self._gdi_hdc = self._d3d.get_dc()
        return self._gdi_hdc

    def end_frame(self, dirty_rects=None):
        if len(self._buf):
            self._d3d.draw_rects(self._buf)
        if self._gdi_hdc is not None:
            self._d3d.release_dc()
            self._gdi_hdc = None
        self._d3d.end()

    def draw_rect(self, x1, y1, x2, y2, color, outline=None, width=1):
        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            return
        key = str(color)
        c = self._color_cache.get(key)
        if c is None:
            r, g, b = _rgb(key)
            c = (r / 255.0, g / 255.0, b / 255.0)
            self._color_cache[key] = c
        cr, cg, cb = c
        self._buf.extend([
            float(x1 - self._ox), float(y1 - self._oy),
            float(w), float(h), cr, cg, cb, 1.0])

    def get_rect_dc(self, w, h, color):
        return None

    def register_sprite(self, x, y, w, h, r, g, b, a):
        return self._d3d.register_sprite(x, y, w, h, r, g, b, a)

    def set_sprite_pos(self, idx, x, y):
        self._d3d.set_sprite_pos(idx, x, y)

    def render_psprites(self):
        self._d3d.render_psprites()

    def resize(self, w, h):
        self._d3d.resize(w, h)

    def draw_text(self, x, y, content, color, font, size, weight, slant, anchor):
        # GDI overlay onto the DXGI back buffer DC (visible after Present)
        import ctypes
        from . import win32
        key = (font, size, weight, slant)
        hfont = self._fonts.get(key)
        if hfont is None:
            hfont = self._get_font(font, size, weight == "bold", slant == "italic")
            self._fonts[key] = hfont
        hdc = self._hdc()
        old = win32.gdi32.SelectObject(hdc, hfont)
        r, g, b = _rgb(str(color))
        win32.gdi32.SetTextColor(hdc, r | (g << 8) | (b << 16))
        win32.gdi32.SetBkMode(hdc, 1)
        text = str(content)
        extent = win32.SIZE()
        win32.gdi32.GetTextExtentPoint32W(hdc, text, len(text), ctypes.byref(extent))
        tw, th = extent.cx, extent.cy
        ax = -tw // 2; ay = -th // 2
        win32.gdi32.TextOutW(hdc, int(x - self._ox) + ax, int(y - self._oy) + ay, text, len(text))
        win32.gdi32.SelectObject(hdc, old)

    def draw_image(self, x, y, image):
        # Image sprites: convert to cached Surface once, blit to DXGI DC per frame.
        if image is None or not self._decode_root:
            return
        surf = self._image_cache.get(id(image))
        if surf is None:
            from .surface import Surface
            w, h = image.width(), image.height()
            if w <= 0 or h <= 0:
                return
            surf = Surface(w, h)
            has_trans = hasattr(image, "transparency_get")
            for py in range(h):
                for px in range(w):
                    r, g, b = image.get(px, py)
                    a = 0 if (has_trans and image.transparency_get(px, py)) else 255
                    surf.set_at(px, py, (r, g, b, a))
            self._image_cache[id(image)] = surf
        ox = int(x - self._ox - surf.width / 2)
        oy = int(y - self._oy - surf.height / 2)
        surf.blit(self._hdc(), ox, oy)

    def close(self):
        try:
            self._d3d.shutdown()
        except Exception:
            pass
        super().close()
