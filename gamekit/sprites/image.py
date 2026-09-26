"""图像加载与处理。

基于标准库 tkinter 的 ``PhotoImage``（支持 PNG / GIF / PPM / PGM / BMP），
并自研了任意角度旋转与任意倍率缩放的像素级算法，不依赖任何第三方库。

注意：旋转 / 非整数缩放使用最近邻像素重采样，只建议在加载时使用一次；
对超大图片（如 300x300 以上）会比较慢，属于标准库方案的能力边界。
"""

import math
import tkinter as tk

# PhotoImage 透明检测能力（Tk 8.6+）。不可用时退回"全不透明"处理。
_HAS_TRANSPARENCY = hasattr(tk.PhotoImage, "transparency_get")


def load_image(path):
    """从文件加载图像，返回一个只读图像对象。

    支持格式：
    - PNG / GIF / PPM / PGM / BMP：走 tkinter PhotoImage
    - JPG / JPEG：Windows 下走 GDI+（ctypes，零依赖）
    """
    low = str(path).lower()
    if low.endswith((".jpg", ".jpeg")):
        import sys
        if sys.platform == "win32":
            from ..render import gdiplus
            return gdiplus.load(path)
        # 非 Windows：Tk 试一下，不行就抛
    photo = tk.PhotoImage(file=path)
    return photo


def _resample(photo, new_w, new_h):
    """最近邻重采样到指定宽高。"""
    src_w, src_h = photo.width(), photo.height()
    if new_w <= 0 or new_h <= 0:
        raise ValueError("缩放后尺寸必须为正数")
    img = tk.PhotoImage(width=new_w, height=new_h)
    _trans = _HAS_TRANSPARENCY
    for ny in range(new_h):
        sy = min(int((ny + 0.5) * src_h / new_h), src_h - 1)
        for nx in range(new_w):
            sx = min(int((nx + 0.5) * src_w / new_w), src_w - 1)
            if _trans and photo.transparency_get(sx, sy):
                continue  # 保持目标像素透明
            r, g, b = photo.get(sx, sy)
            img.put("#%02x%02x%02x" % (r, g, b), to=(nx, ny))
    return img


def scale_image(photo, factor):
    """按倍率缩放图像。``factor`` 可为任意正浮点数。"""
    if factor == 1.0:
        return photo
    # 整数放大直接用 Tk 的 zoom（快）
    if factor > 1 and abs(factor - round(factor)) < 1e-9:
        return photo.zoom(int(round(factor)))
    # 整数缩小直接用 Tk 的 subsample（快）
    if factor < 1 and abs(1.0 / factor - round(1.0 / factor)) < 1e-9:
        return photo.subsample(int(round(1.0 / factor)))
    # 其余情况走最近邻重采样
    new_w = max(1, int(round(photo.width() * factor)))
    new_h = max(1, int(round(photo.height() * factor)))
    return _resample(photo, new_w, new_h)


def _rotate90(photo):
    return _resample_transpose(photo, "cw")


def _rotate180(photo):
    return _resample_transpose(photo, "180")


def _rotate270(photo):
    return _resample_transpose(photo, "ccw")


def _resample_transpose(photo, mode):
    """90 / 180 / 270 度的快速旋转（像素换位，不做插值）。"""
    src_w, src_h = photo.width(), photo.height()
    if mode == "cw":
        new_w, new_h = src_h, src_w
    elif mode == "ccw":
        new_w, new_h = src_h, src_w
    else:
        new_w, new_h = src_w, src_h
    img = tk.PhotoImage(width=new_w, height=new_h)
    _trans = _HAS_TRANSPARENCY
    for sy in range(src_h):
        for sx in range(src_w):
            if _trans and photo.transparency_get(sx, sy):
                continue
            r, g, b = photo.get(sx, sy)
            color = "#%02x%02x%02x" % (r, g, b)
            if mode == "cw":
                nx, ny = src_h - 1 - sy, sx
            elif mode == "ccw":
                nx, ny = sy, src_w - 1 - sx
            else:
                nx, ny = src_w - 1 - sx, src_h - 1 - sy
            img.put(color, to=(nx, ny))
    return img


def flip_image(photo, horizontal=False, vertical=False):
    """水平 / 垂直翻转图像，返回新 PhotoImage（等价于 pygame.transform.flip）。"""
    if not horizontal and not vertical:
        return photo
    src_w, src_h = photo.width(), photo.height()
    img = tk.PhotoImage(width=src_w, height=src_h)
    _trans = _HAS_TRANSPARENCY
    for sy in range(src_h):
        for sx in range(src_w):
            nx = src_w - 1 - sx if horizontal else sx
            ny = src_h - 1 - sy if vertical else sy
            if _trans and photo.transparency_get(sx, sy):
                continue
            r, g, b = photo.get(sx, sy)
            img.put("#%02x%02x%02x" % (r, g, b), to=(nx, ny))
    return img


def rotate_image(photo, angle):
    """按角度（度）旋转图像，返回新 PhotoImage。"""
    angle = angle % 360
    if angle == 0:
        return photo
    if abs(angle - 90) < 0.5:
        return _rotate90(photo)
    if abs(angle - 180) < 0.5:
        return _rotate180(photo)
    if abs(angle - 270) < 0.5:
        return _rotate270(photo)
    return _rotate_any(photo, angle)


def _rotate_any(photo, angle):
    """任意角度旋转（最近邻 + 反向映射，保持透明）。"""
    src_w, src_h = photo.width(), photo.height()
    cx, cy = (src_w - 1) / 2.0, (src_h - 1) / 2.0
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    new_w = int(abs(src_w * cos_a) + abs(src_h * sin_a)) + 1
    new_h = int(abs(src_w * sin_a) + abs(src_h * cos_a)) + 1
    img = tk.PhotoImage(width=new_w, height=new_h)
    ncx, ncy = (new_w - 1) / 2.0, (new_h - 1) / 2.0
    _trans = _HAS_TRANSPARENCY

    for ny in range(new_h):
        for nx in range(new_w):
            dx = nx - ncx
            dy = ny - ncy
            # 反向旋转找到源像素
            sx = dx * cos_a + dy * sin_a + cx
            sy = -dx * sin_a + dy * cos_a + cy
            ix = int(round(sx))
            iy = int(round(sy))
            if 0 <= ix < src_w and 0 <= iy < src_h:
                if _trans and photo.transparency_get(ix, iy):
                    continue
                r, g, b = photo.get(ix, iy)
                img.put("#%02x%02x%02x" % (r, g, b), to=(nx, ny))
    return img
