"""Windows 摄像头支持（ctypes 绑 avicap32.dll，零第三方依赖）。

用老式 AVI 捕获 API：创建一个隐藏捕获窗口、连接摄像头驱动、
抓一帧、从剪贴板拿 HBITMAP、读像素。返回一个 duck-type 兼容
tk.PhotoImage 的对象，直接可喂给 Sprite。

仅 Windows。没有摄像头 / 被占用时 ``Camera.open()`` 返回 None。
"""
import ctypes
from ctypes import wintypes
import sys

if sys.platform != "win32":
    _avicap = None
else:
    _avicap = ctypes.windll.avicap32
    _user32 = ctypes.windll.user32
    _gdi32 = ctypes.windll.gdi32

_WM_CAP_START = 0x0400
_WM_CAP_DRIVER_CONNECT = _WM_CAP_START + 10
_WM_CAP_DRIVER_DISCONNECT = _WM_CAP_START + 11
_WM_CAP_GRAB_FRAME = _WM_CAP_START + 60
_WM_CAP_EDIT_COPY = _WM_CAP_START + 30


class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", wintypes.LONG),
        ("bmWidth", wintypes.LONG),
        ("bmHeight", wintypes.LONG),
        ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes", wintypes.WORD),
        ("bmBitsPixel", wintypes.WORD),
        ("bmBits", ctypes.c_void_p),
    ]


class CameraFrame:
    """一帧摄像头图像，duck-type 兼容 PhotoImage 的只读接口。"""

    def __init__(self, width, height, pixels_bgr):
        self._w = width
        self._h = height
        self._px = pixels_bgr   # bytes，BGR 顺序，w*h*3

    def width(self):
        return self._w

    def height(self):
        return self._h

    def get(self, x, y):
        i = (y * self._w + x) * 3
        b = self._px[i]
        g = self._px[i + 1]
        r = self._px[i + 2]
        return (r, g, b)


class Camera:
    """打开默认摄像头。``Camera.open()`` 返回实例或 None。"""

    def __init__(self, hwnd):
        self._hwnd = hwnd
        self._open = True

    @staticmethod
    def open(index=0, width=640, height=480):
        if _avicap is None:
            return None
        # 隐藏捕获窗口
        hwnd = _avicap.capCreateCaptureWindowW(
            "gamekit_cam",
            0, 0, 0, 0,
            0, 0,   # 父窗口 / 父句柄 0
            0)
        if not hwnd:
            return None
        rc = _user32.SendMessageW(hwnd, _WM_CAP_DRIVER_CONNECT, index, 0)
        if not rc:
            _user32.DestroyWindow(hwnd)
            return None
        return Camera(hwnd)

    def grab(self):
        """抓一帧，返回 CameraFrame。失败返回 None。"""
        if not self._open:
            return None
        # 抓单帧
        _user32.SendMessageW(self._hwnd, _WM_CAP_GRAB_FRAME, 0, 0)
        # 拷到剪贴板
        _user32.SendMessageW(self._hwnd, _WM_CAP_EDIT_COPY, 0, 0)
        if not _user32.OpenClipboard(0):
            return None
        hbitmap = _user32.GetClipboardData(2)   # CF_BITMAP
        frame = None
        if hbitmap:
            bm = BITMAP()
            _gdi32.GetObjectW(hbitmap, ctypes.sizeof(BITMAP), ctypes.byref(bm))
            w, h = bm.bmWidth, bm.bmHeight
            row_bytes = ((w * 3 + 3) // 4) * 4   # 4 字节对齐
            size = row_bytes * h
            buf = ctypes.create_string_buffer(size)
            _gdi32.GetBitmapBits(hbitmap, size, buf)
            frame = CameraFrame(w, h, bytes(buf.raw))
        _user32.CloseClipboard()
        return frame

    def close(self):
        if self._open:
            _user32.SendMessageW(self._hwnd, _WM_CAP_DRIVER_DISCONNECT, 0, 0)
            _user32.DestroyWindow(self._hwnd)
            self._open = False
