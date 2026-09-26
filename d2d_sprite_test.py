"""Test: C-side sprite array rendering (zero Python per-frame iteration)."""
import sys, time, random
sys.path.insert(0, r"C:\Users\Administrator\Desktop\new-chat")

import ctypes
from ctypes import wintypes

ctypes.windll.ole32.CoInitializeEx(None, 0x2)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT,
                              wintypes.WPARAM, wintypes.LPARAM)

def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == 0x0002:
        user32.PostQuitMessage(0)
        return 0
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
               ctypes.c_void_p(1), None, "D2DSprTest")
user32.RegisterClassW(ctypes.byref(wc))
hwnd = user32.CreateWindowExW(
    0, "D2DSprTest", "D2D Sprite Array Test",
    0x00CF0000, 100, 100, 800, 600, None, None, hInst, None)
user32.ShowWindow(hwnd, 5)

from gamekit import _d2d
_d2d.init(hwnd)
print("D2D init OK")

# Register 4000 sprites (one-time Python->C calls)
random.seed(1)
N = 4000
for i in range(N):
    x = (i * 7) % 760
    y = (i * 13) % 560
    r = ((i * 37) % 256) / 255.0
    g = ((i * 91) % 256) / 255.0
    b = ((i * 53) % 256) / 255.0
    _d2d.add_sprite(float(x), float(y), 32.0, 32.0, r, g, b, 1.0)
print(f"Registered {N} sprites in C array")
_d2d.sort_sprites()

msg = wintypes.MSG()
t0 = time.perf_counter()
frames = 0

while time.perf_counter() - t0 < 3:
    while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
    _d2d.begin(0.1, 0.15, 0.3, 1.0)
    _d2d.render_batched(0.0, 0.0)
    _d2d.end()
    frames += 1

elapsed = time.perf_counter() - t0
print(f"{N} sprites C-array: {frames / elapsed:.1f} FPS")
_d2d.shutdown()
