"""Windows GDI+ 图像解码（ctypes，零第三方依赖）。

用 gdiplus.dll 解码 JPG / BMP / PNG / GIF 等 GDI+ 支持的格式，
返回一个 duck-type 兼容 ``tk.PhotoImage`` 的对象：
实现 ``width() / height() / get(x, y) -> (r, g, b)``。
GdiRenderer 读像素时不关心底层是 Tk 还是 GDI+。
"""
import ctypes
from ctypes import wintypes
import os

_gdiplus = None
_token = None


def _ensure_gdiplus():
    global _gdiplus, _token
    if _gdiplus is not None:
        return
    gdi = ctypes.windll.gdiplus

    class GdiplusStartupInput(ctypes.Structure):
        _fields_ = [
            ("GdiplusVersion", wintypes.UINT),
            ("DebugEventCallback", ctypes.c_void_p),
            ("SuppressBackgroundThread", wintypes.BOOL),
            ("SuppressExternalCodecs", wintypes.BOOL),
        ]

    si = GdiplusStartupInput()
    si.GdiplusVersion = 1
    token = wintypes.ULONG()
    gdi.GdiplusStartup(ctypes.byref(token), ctypes.byref(si), None)
    _gdiplus = gdi
    _token = token.value


class GdipImage:
    """GDI+ 解码出的图像，duck-type 兼容 tk.PhotoImage 的只读接口。"""

    def __init__(self, gpimage, width, height, pixels):
        self._gp = gpimage
        self._w = width
        self._h = height
        self._px = pixels   # bytes，BGRA 顺序，w*h*4

    def width(self):
        return self._w

    def height(self):
        return self._h

    def get(self, x, y):
        i = (y * self._w + x) * 4
        b = self._px[i]
        g = self._px[i + 1]
        r = self._px[i + 2]
        return (r, g, b)


# PixelFormat32bppARGB
_PIXFMT_32BPP_ARGB = 0x26200A
_IMAGELOCK_READ = 0x0001


class _BitmapData(ctypes.Structure):
    _fields_ = [
        ("Width", wintypes.UINT),
        ("Height", wintypes.UINT),
        ("Stride", ctypes.c_int),
        ("PixelFormat", wintypes.INT),
        ("Scan0", ctypes.c_void_p),
        ("Reserved", ctypes.c_void_p),
    ]


class _Rect(ctypes.Structure):
    _fields_ = [
        ("X", ctypes.c_int),
        ("Y", ctypes.c_int),
        ("Width", ctypes.c_int),
        ("Height", ctypes.c_int),
    ]


def load(path):
    """从文件解码任意 GDI+ 支持的格式（JPG/BMP/PNG/GIF/TIFF）。"""
    _ensure_gdiplus()
    gdi = _gdiplus
    gpimage = ctypes.c_void_p()
    rc = gdi.GdipLoadImageFromFile(str(path), ctypes.byref(gpimage))
    if rc != 0:
        raise IOError("GDI+ 无法解码图像: %s (code %d)" % (path, rc))

    w = wintypes.UINT()
    h = wintypes.UINT()
    gdi.GdipGetImageWidth(gpimage, ctypes.byref(w))
    gdi.GdipGetImageHeight(gpimage, ctypes.byref(h))
    W, H = w.value, h.value

    rect = _Rect(0, 0, W, H)
    bd = _BitmapData()
    gdi.GdipBitmapLockBits(gpimage, ctypes.byref(rect), _IMAGELOCK_READ,
                           _PIXFMT_32BPP_ARGB, ctypes.byref(bd))
    try:
        stride = bd.Stride
        size = abs(stride) * H
        import ctypes as _ct
        buf = (_ct.c_ubyte * size).from_address(bd.Scan0)
        pixels = bytes(buf)
    finally:
        gdi.GdipBitmapUnlockBits(gpimage, ctypes.byref(bd))

    # 规整成 width*height*4 的连续 BGRA（stride 可能 > width*4，或负）
    if stride == W * 4:
        flat = pixels
    else:
        flat = bytearray(W * H * 4)
        for row in range(H):
            src = row * stride
            flat[row*W*4:(row+1)*W*4] = pixels[src:src+W*4]
        flat = bytes(flat)

    return GdipImage(gpimage, W, H, flat)
