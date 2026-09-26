# gamekit.render.surface
# Surface：一块 32 位 ARGB 像素缓冲 + 一个内存 DC。
# 对应 pygame.Surface 的角色。精灵（sprite）以后就是一个 Surface：
# 创建时把形状/图像画进像素，运行时整块 blit 走，而不是每帧重算矢量。

import ctypes
from ctypes import c_void_p, c_uint32, byref

from . import win32

_BLEND_AC_SRC_ALPHA = 0x01


class _BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class Surface:
    """一块像素缓冲。宽度 height 单位为像素，内存是 BGRA 字节序。

    用 GDI 的 CreateDIBSection 分配：返回的像素内存可以直接被 Python
    读写（fill / set_at），也能被 BitBlt / AlphaBlend 整块搬运。
    """

    __slots__ = ("width", "height", "_hdc", "_hbmp", "_bits", "_buf")

    def __init__(self, width, height):
        if width <= 0 or height <= 0:
            raise ValueError("Surface size must be positive: %dx%d" % (width, height))
        self.width = int(width)
        self.height = int(height)

        bmi = win32.BITMAPINFO()
        hdr = bmi.bmiHeader
        hdr.biSize = ctypes.sizeof(win32.BITMAPINFOHEADER)
        hdr.biWidth = self.width
        hdr.biHeight = -self.height        # 负值 = top-down（第 0 行在最上面）
        hdr.biPlanes = 1
        hdr.biBitCount = 32                # 32 位 BGRA
        hdr.biCompression = 0              # BI_RGB

        bits = c_void_p()
        hdc = win32.gdi32.CreateCompatibleDC(None)
        if not hdc:
            raise OSError("CreateCompatibleDC failed")
        hbmp = win32.gdi32.CreateDIBSection(hdc, byref(bmi), win32.DIB_RGB_COLORS,
                                            byref(bits), None, 0)
        if not hbmp:
            win32.gdi32.DeleteDC(hdc)
            raise OSError("CreateDIBSection failed")
        win32.gdi32.SelectObject(hdc, hbmp)

        self._hdc = hdc
        self._hbmp = hbmp
        self._bits = bits
        # 把像素内存包成可索引的 uint32 数组
        self._buf = (c_uint32 * (self.width * self.height)).from_address(bits.value)

    # ------------------------------------------------------------ 属性

    @property
    def size(self):
        return (self.width, self.height)

    @property
    def dc(self):
        """这个 Surface 的内存 DC，供 BitBlt 做源。"""
        return self._hdc

    # ------------------------------------------------------------ 像素操作

    def fill(self, color):
        """整块填充。color 为 (r,g,b) 或 (r,g,b,a)。

        用字节模板 + 一次 memmove（C 层），而不是 Python 逐像素循环。
        640x400 一帧约 1MB，一次拷贝搞定。
        """
        r, g, b = color[0], color[1], color[2]
        a = color[3] if len(color) > 3 else 255
        px = bytes((b, g, r, a))
        blob = px * (self.width * self.height)
        ctypes.memmove(self._bits, blob, len(blob))

    def set_at(self, x, y, color):
        """设置单个像素。x,y 越界直接忽略（不抛错）。"""
        if 0 <= x < self.width and 0 <= y < self.height:
            r, g, b = color[0], color[1], color[2]
            a = color[3] if len(color) > 3 else 255
            self._buf[y * self.width + x] = win32.pixel_uint(r, g, b, a)

    def get_at(self, x, y):
        """读取单个像素，返回 (r,g,b,a)。"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return (0, 0, 0, 0)
        v = self._buf[y * self.width + x]
        return (v >> 16 & 0xFF, v >> 8 & 0xFF, v & 0xFF, v >> 24 & 0xFF)

    # ------------------------------------------------------------ blit

    def blit(self, dst_dc, dx, dy, alpha=False):
        """把本 Surface 整块位块传送到目标 DC 的 (dx, dy)。

        alpha=False：SRCCOPY 硬拷贝（速度快，忽略 alpha 通道）。
        alpha=True ：AlphaBlend 带透明混合（按每个像素的 alpha 合成）。
        """
        w, h = self.width, self.height
        if alpha:
            bf = _BLENDFUNCTION()
            bf.BlendOp = 0                # AC_SRC_OVER
            bf.BlendFlags = 0
            bf.SourceConstantAlpha = 255
            bf.AlphaFormat = _BLEND_AC_SRC_ALPHA
            win32.msimg32.AlphaBlend(dst_dc, dx, dy, w, h,
                                     self._hdc, 0, 0, w, h, byref(bf))
        else:
            win32.gdi32.BitBlt(dst_dc, dx, dy, w, h,
                               self._hdc, 0, 0, win32.SRCCOPY)

    # ------------------------------------------------------------ 释放

    def close(self):
        """释放 GDI 资源。Surface 用完后要调，否则句柄泄漏。"""
        if self._hbmp:
            win32.gdi32.DeleteObject(self._hbmp)
            self._hbmp = None
        if self._hdc:
            win32.gdi32.DeleteDC(self._hdc)
            self._hdc = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
