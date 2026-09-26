# gamekit.render.win32
# Win32 / GDI 绑定的最底层。全部用标准库 ctypes 手写，零第三方依赖。
# 这里只做一件事：把 Windows 系统图形接口的函数和结构体声明出来，
# 供上层的 Surface / Window 调用。核心是 CreateDIBSection（像素缓冲）
# 和 BitBlt（整块像素位块传送）——这就是 pygame 底下 SDL 干的事，
# 我们用自己的代码直接调系统，绕过 tkinter。

import ctypes
from ctypes import (
    c_int32, c_uint16, c_uint32, c_size_t, c_ssize_t,
    c_void_p, c_wchar_p, c_long, c_int, POINTER, byref, sizeof, Structure,
)

# ---------------------------------------------------------------- 常量

BI_RGB = 0
DIB_RGB_COLORS = 0
SRCCOPY = 0x00CC0020
PM_REMOVE = 0x0001
WM_QUIT = 0x0012
CW_USEDEFAULT = 0x80000000

WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_VISIBLE = 0x10000000
WS_EX_APPWINDOW = 0x00040000

COLOR_WINDOW = 5
DC_BRUSH = 18
DC_PEN = 19

VK_ESCAPE = 0x1B

# GDI 绘制常量
TRANSPARENT = 1
OPAQUE = 2
PS_SOLID = 0
DEFAULT_CHARSET = 1
OUT_DEFAULT_PRECIS = 0
CLIP_DEFAULT_PRECIS = 0
DEFAULT_QUALITY = 0
DEFAULT_PITCH = 0
FF_DONTCARE = 0
FW_NORMAL = 400
FW_BOLD = 700

# ---------------------------------------------------------------- 结构体

class BITMAPINFOHEADER(Structure):
    _fields_ = [
        ("biSize", c_uint32),
        ("biWidth", c_int32),
        ("biHeight", c_int32),
        ("biPlanes", c_uint16),
        ("biBitCount", c_uint16),
        ("biCompression", c_uint32),
        ("biSizeImage", c_uint32),
        ("biXPelsPerMeter", c_int32),
        ("biYPelsPerMeter", c_int32),
        ("biClrUsed", c_uint32),
        ("biClrImportant", c_uint32),
    ]

class BITMAPINFO(Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", c_uint32 * 1),
    ]

class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]

class SIZE(Structure):
    _fields_ = [("cx", c_long), ("cy", c_long)]

class MSG(Structure):
    _fields_ = [
        ("hwnd", c_void_p),
        ("message", c_uint32),
        ("wParam", c_size_t),
        ("lParam", c_ssize_t),
        ("time", c_uint32),
        ("pt", POINT),
    ]

# 窗口过程回调类型：LONG WINAPI WndProc(HWND, UINT, WPARAM, LPARAM)
WNDPROC = ctypes.WINFUNCTYPE(c_ssize_t, c_void_p, c_uint32, c_size_t, c_ssize_t)

class WNDCLASSW(Structure):
    _fields_ = [
        ("style", c_uint32),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", c_int32),
        ("cbWndExtra", c_int32),
        ("hInstance", c_void_p),
        ("hIcon", c_void_p),
        ("hCursor", c_void_p),
        ("hbrBackground", c_void_p),
        ("lpszMenuName", c_wchar_p),
        ("lpszClassName", c_wchar_p),
    ]

# ---------------------------------------------------------------- 库句柄

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32
msimg32 = ctypes.windll.msimg32  # 提供 AlphaBlend（透明混合，阶段2再用）

# ---------------------------------------------------------------- kernel32

kernel32.GetModuleHandleW.argtypes = [c_wchar_p]
kernel32.GetModuleHandleW.restype = c_void_p

# ---------------------------------------------------------------- user32

user32.RegisterClassW.argtypes = [POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = c_uint16

user32.CreateWindowExW.argtypes = [
    c_uint32, c_wchar_p, c_wchar_p, c_uint32,
    c_int32, c_int32, c_int32, c_int32,
    c_void_p, c_void_p, c_void_p, c_void_p,
]
user32.CreateWindowExW.restype = c_void_p

user32.ShowWindow.argtypes = [c_void_p, c_int32]
user32.ShowWindow.restype = c_int32

user32.UpdateWindow.argtypes = [c_void_p]
user32.UpdateWindow.restype = c_int32

user32.DestroyWindow.argtypes = [c_void_p]
user32.DestroyWindow.restype = c_int32

user32.DefWindowProcW.argtypes = [c_void_p, c_uint32, c_size_t, c_ssize_t]
user32.DefWindowProcW.restype = c_ssize_t

user32.PostQuitMessage.argtypes = [c_int32]
user32.PostQuitMessage.restype = None

user32.GetDC.argtypes = [c_void_p]
user32.GetDC.restype = c_void_p

user32.ReleaseDC.argtypes = [c_void_p, c_void_p]
user32.ReleaseDC.restype = c_int32

user32.PeekMessageW.argtypes = [POINTER(MSG), c_void_p, c_uint32, c_uint32, c_uint32]
user32.PeekMessageW.restype = c_int32

user32.TranslateMessage.argtypes = [POINTER(MSG)]
user32.TranslateMessage.restype = c_int32

user32.DispatchMessageW.argtypes = [POINTER(MSG)]
user32.DispatchMessageW.restype = c_ssize_t

user32.SetWindowTextW.argtypes = [c_void_p, c_wchar_p]
user32.SetWindowTextW.restype = c_int32

# 键盘：GetAsyncKeyState 直接轮询，高位为 1 表示按下
user32.GetAsyncKeyState.argtypes = [c_int32]
user32.GetAsyncKeyState.restype = c_uint16

user32.GetCursorPos.argtypes = [POINTER(POINT)]
user32.GetCursorPos.restype = c_int32

user32.ScreenToClient.argtypes = [c_void_p, POINTER(POINT)]
user32.ScreenToClient.restype = c_int32

user32.FillRect.argtypes = [c_void_p, POINTER(c_long * 4), c_void_p]
user32.FillRect.restype = c_int32

# ---------------------------------------------------------------- gdi32

gdi32.CreateCompatibleDC.argtypes = [c_void_p]
gdi32.CreateCompatibleDC.restype = c_void_p

gdi32.DeleteDC.argtypes = [c_void_p]
gdi32.DeleteDC.restype = c_int32

gdi32.CreateDIBSection.argtypes = [
    c_void_p, POINTER(BITMAPINFO), c_uint32, POINTER(c_void_p), c_void_p, c_uint32,
]
gdi32.CreateDIBSection.restype = c_void_p

gdi32.SelectObject.argtypes = [c_void_p, c_void_p]
gdi32.SelectObject.restype = c_void_p

gdi32.DeleteObject.argtypes = [c_void_p]
gdi32.DeleteObject.restype = c_int32

gdi32.BitBlt.argtypes = [
    c_void_p, c_int32, c_int32, c_int32, c_int32,
    c_void_p, c_int32, c_int32, c_uint32,
]
gdi32.BitBlt.restype = c_int32

gdi32.StretchBlt.argtypes = [
    c_void_p, c_int32, c_int32, c_int32, c_int32,
    c_void_p, c_int32, c_int32, c_int32, c_int32, c_uint32,
]
gdi32.StretchBlt.restype = c_int32

gdi32.GetStockObject.argtypes = [c_int32]
gdi32.GetStockObject.restype = c_void_p

gdi32.SetDCBrushColor.argtypes = [c_void_p, c_uint32]
gdi32.SetDCBrushColor.restype = c_uint32

# 形状绘制（画到 DC 上，DIB DC 也适用）
gdi32.Ellipse.argtypes = [c_void_p, c_int32, c_int32, c_int32, c_int32]
gdi32.Ellipse.restype = c_int32

gdi32.MoveToEx.argtypes = [c_void_p, c_int32, c_int32, c_void_p]
gdi32.MoveToEx.restype = c_int32

gdi32.LineTo.argtypes = [c_void_p, c_int32, c_int32]
gdi32.LineTo.restype = c_int32

gdi32.Polygon.argtypes = [c_void_p, POINTER(c_long), c_int32]
gdi32.Polygon.restype = c_int32

gdi32.Arc.argtypes = [c_void_p, c_int32, c_int32, c_int32, c_int32,
                      c_int32, c_int32, c_int32, c_int32]
gdi32.Arc.restype = c_int32

# 画笔 / 字体 / 文本
gdi32.CreatePen.argtypes = [c_int32, c_int32, c_uint32]
gdi32.CreatePen.restype = c_void_p

gdi32.SetDCPenColor.argtypes = [c_void_p, c_uint32]
gdi32.SetDCPenColor.restype = c_uint32

gdi32.CreateFontW.argtypes = [
    c_int32, c_int32, c_int32, c_int32, c_int32, c_uint32, c_uint32, c_uint32,
    c_uint32, c_uint32, c_uint32, c_uint32, c_uint32, c_wchar_p,
]
gdi32.CreateFontW.restype = c_void_p

gdi32.SetTextColor.argtypes = [c_void_p, c_uint32]
gdi32.SetTextColor.restype = c_uint32

gdi32.SetBkMode.argtypes = [c_void_p, c_int32]
gdi32.SetBkMode.restype = c_int32

gdi32.TextOutW.argtypes = [c_void_p, c_int32, c_int32, c_wchar_p, c_int32]
gdi32.TextOutW.restype = c_int32

gdi32.GetTextExtentPoint32W.argtypes = [c_void_p, c_wchar_p, c_int32, c_void_p]
gdi32.GetTextExtentPoint32W.restype = c_int32

# AlphaBlend：带透明度的整块位块传送（阶段2 用）
msimg32.AlphaBlend.argtypes = [
    c_void_p, c_int32, c_int32, c_int32, c_int32,
    c_void_p, c_int32, c_int32, c_int32, c_int32, c_void_p,
]
msimg32.AlphaBlend.restype = c_int32


# ---------------------------------------------------------------- 工具

def pixel_uint(r, g, b, a=255):
    """(r,g,b,a) -> 内存中的 uint32 值。32 位 DIB 内存字节序是 B,G,R,A。"""
    return (b & 0xFF) | ((g & 0xFF) << 8) | ((r & 0xFF) << 16) | ((a & 0xFF) << 24)


def hinstance():
    return kernel32.GetModuleHandleW(None)
