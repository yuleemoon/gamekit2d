"""D2D 渲染测试：创建窗口 + 画矩形动画。"""
import sys, time
sys.path.insert(0, r"C:\Users\Administrator\Desktop\new-chat")

import ctypes
from ctypes import wintypes

# Init COM
ctypes.windll.ole32.CoInitializeEx(None, 0x2)

# Create Win32 window
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT,
                              wintypes.WPARAM, wintypes.LPARAM)

def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == 0x0002:
        user32.PostQuitMessage(0)
        return 0
    user32.DefWindowProcW.restype = ctypes.c_long
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                       wintypes.WPARAM, wintypes.LPARAM]
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

wndproc = WNDPROC(wnd_proc)

class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
    ]

hInst = kernel32.GetModuleHandleW(None)
wc = WNDCLASSW(0, wndproc, 0, 0, hInst, None, None,
               ctypes.c_void_p(1), None, "D2DTest")
user32.RegisterClassW(ctypes.byref(wc))

hwnd = user32.CreateWindowExW(
    0, "D2DTest", "Direct2D Test",
    0x00CF0000, 100, 100, 800, 600,
    None, None, hInst, None)
user32.ShowWindow(hwnd, 5)

# Init D2D
from gamekit import _d2d
_d2d.init(hwnd)
print("D2D initialized!")

# Animation loop
import random
random.seed(1)
rects = []
for i in range(4000):
    rects.append((
        random.randint(0, 760), random.randint(0, 560),
        32, 32,
        random.random(), random.random(), random.random(), 1.0))

msg = wintypes.MSG()
t0 = time.perf_counter()
frames = 0

while time.perf_counter() - t0 < 3:
    while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    _d2d.begin(0.1, 0.15, 0.3, 1.0)
    for (x, y, w, h, r, g, b, a) in rects:
        _d2d.fill_rect(x, y, w, h, r, g, b, a)
    _d2d.end()
    frames += 1

elapsed = time.perf_counter() - t0
print("4000 rects: %.1f FPS" % (frames / elapsed))
_d2d.shutdown()
