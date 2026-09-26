# gamekit.render.window
# Window：用 Win32 原生 API 创建的窗口，带双缓冲渲染和输入状态。
# 双缓冲 = 一个后台 Surface（DIB）+ 窗口 DC；每帧所有精灵先画到后台，
# present() 一次性 BitBlt 翻到屏幕。这就是 pygame 里 flip() 做的事。

import ctypes
from ctypes import byref, c_int32, c_size_t, c_ssize_t, c_void_p

from . import win32
from .surface import Surface
from .win32 import MSG, POINT, WNDCLASSW

# 窗口消息常量
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_MOUSEWHEEL = 0x020A

_CLASS_NAME = "GameKitRenderWindow"

# 所有活着的 Window：hwnd -> Window，供 wndproc 回调（滚轮等）反查实例
_WINDOWS = {}
# 窗口类只注册一次（重复 RegisterClassW 会让类句柄和 WNDPROC 闭包累积）
_class_registered = False


@win32.WNDPROC
def _wndproc(hwnd, msg, wparam, lparam):
    """模块级窗口过程：不闭包，所有 GameKit 窗口共享。"""
    if msg == WM_MOUSEWHEEL:
        win = _WINDOWS.get(hwnd)
        if win is not None:
            delta = (wparam >> 16) & 0xFFFF
            if delta >= 0x8000:
                delta -= 0x10000
            win._wheel_delta += delta
        return 0
    if msg == WM_CLOSE:
        win32.user32.DestroyWindow(hwnd)
        return 0
    if msg == WM_DESTROY:
        # 注意：这里不要 PostQuitMessage(0)。
        # PostQuitMessage 会往线程消息队列塞 WM_QUIT，
        # 若同进程随后再用 tkinter（Tcl 事件循环），残留的
        # WM_QUIT 会让其悄悄退出。关闭检测改由 poll_events 的
        # IsWindow 完成。
        return 0
    return win32.user32.DefWindowProcW(hwnd, msg, wparam, lparam)


class Window:
    """一个原生窗口，内部是 后台Surface + 窗口DC 的双缓冲。

    用法：
        w = Window(640, 480, "demo")
        while w.poll_events():
            # ... 画到 w.screen（一个 Surface）
            w.present()          # 翻屏
        w.close()
    """

    def __init__(self, width, height, title="gamekit"):
        self.width = int(width)
        self.height = int(height)
        self._hwnd = None
        self._wndproc = None      # 保持回调引用，防止被 GC
        self._screen = None       # 后台缓冲（双缓冲的"后"半）
        self._dc = None           # 窗口 DC
        self._closed = False

        self._register_class()
        self._create_window(title)
        self._screen = Surface(self.width, self.height)
        self._dc = win32.user32.GetDC(self._hwnd)
        if not self._dc:
            raise OSError("GetDC failed")

    # ------------------------------------------------------------ 创建

    def _register_class(self):
        global _class_registered
        if not _class_registered:
            wc = WNDCLASSW()
            wc.style = 0
            wc.lpfnWndProc = _wndproc
            wc.cbClsExtra = 0
            wc.cbWndExtra = 0
            wc.hInstance = win32.hinstance()
            wc.hIcon = None
            wc.hCursor = None
            wc.hbrBackground = win32.gdi32.GetStockObject(win32.COLOR_WINDOW)
            wc.lpszMenuName = None
            wc.lpszClassName = _CLASS_NAME
            if win32.user32.RegisterClassW(byref(wc)):
                _class_registered = True

    def _create_window(self, title):
        style = win32.WS_OVERLAPPEDWINDOW | win32.WS_VISIBLE
        hwnd = win32.user32.CreateWindowExW(
            win32.WS_EX_APPWINDOW, _CLASS_NAME, title, style,
            win32.CW_USEDEFAULT, win32.CW_USEDEFAULT,
            self.width, self.height,
            None, None, win32.hinstance(), None,
        )
        if not hwnd:
            raise OSError("CreateWindowExW failed")
        self._hwnd = hwnd
        self._wheel_delta = 0
        _WINDOWS[hwnd] = self
        win32.user32.ShowWindow(hwnd, 1)   # SW_SHOWNORMAL
        win32.user32.UpdateWindow(hwnd)

    # ------------------------------------------------------------ 属性

    @property
    def screen(self):
        """后台 Surface，游戏每帧往这里画。"""
        return self._screen

    @property
    def closed(self):
        return self._closed

    @property
    def wheel_delta(self):
        """累计滚轮增量（自上次 reset 后）。"""
        return self._wheel_delta

    def reset_wheel(self):
        self._wheel_delta = 0

    # ------------------------------------------------------------ 循环

    def poll_events(self):
        """处理所有待处理窗口消息。返回 False 表示窗口被关闭。"""
        # 窗口可能已被 WM_CLOSE -> DestroyWindow 销毁（无 WM_QUIT 可读），
        # 用 IsWindow 检测真实窗口状态。
        if not self._hwnd or not win32.user32.IsWindow(self._hwnd):
            self._closed = True
            return False
        msg = MSG()
        while win32.user32.PeekMessageW(byref(msg), None, 0, 0, win32.PM_REMOVE):
            win32.user32.TranslateMessage(byref(msg))
            win32.user32.DispatchMessageW(byref(msg))
        return not self._closed

    def present(self, rects=None):
        """把后台缓冲 BitBlt 到窗口。

        rects=None：全屏翻屏（对应 pygame.display.flip()）。
        rects=[(x1,y1,x2,y2), ...]：只更新这些脏区域（局部翻屏，
        静态区域不动，性能更好）。
        """
        if self._screen is None or not self._dc:
            return
        if not rects:
            self._screen.blit(self._dc, 0, 0)
            return
        for x1, y1, x2, y2 in rects:
            w = int(x2 - x1)
            h = int(y2 - y1)
            if w <= 0 or h <= 0:
                continue
            # 只把后台缓冲的 (x1,y1,w,h) 区域 BitBlt 到窗口同位置
            win32.gdi32.BitBlt(self._dc, int(x1), int(y1), w, h,
                                self._screen.dc, int(x1), int(y1), win32.SRCCOPY)

    # ------------------------------------------------------------ 输入

    def is_key_down(self, key):
        """key 为虚拟键码（如 VK_ESCAPE）。高位为 1 = 当前按下。"""
        return bool(win32.user32.GetAsyncKeyState(int(key)) & 0x8000)

    def mouse_pos(self):
        """窗口内的鼠标坐标。"""
        p = POINT()
        win32.user32.GetCursorPos(byref(p))
        win32.user32.ScreenToClient(self._hwnd, byref(p))
        return (p.x, p.y)

    # ------------------------------------------------------------ 释放

    def close(self):
        if self._closed:
            return
        if self._hwnd:
            _WINDOWS.pop(self._hwnd, None)
        if self._dc:
            win32.user32.ReleaseDC(self._hwnd, self._dc)
            self._dc = None
        if self._screen is not None:
            self._screen.close()
            self._screen = None
        if self._hwnd:
            win32.user32.DestroyWindow(self._hwnd)
            self._hwnd = None
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
