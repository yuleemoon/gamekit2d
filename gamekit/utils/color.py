"""颜色工具：预定义颜色常量、颜色转换与混合。

gamekit 内部统一使用 tkinter 可识别的颜色字符串（如 ``"red"``、``"#ff0000"``）。
``Color`` 对象提供更方便的编程体验，任何 API 都同时接受：
字符串、``(r, g, b)`` 元组、``Color`` 实例。
"""

import random


class Color:
    """一个简单的 RGB 颜色对象。"""

    __slots__ = ("r", "g", "b")

    def __init__(self, r, g, b):
        self.r = max(0, min(255, int(r)))
        self.g = max(0, min(255, int(g)))
        self.b = max(0, min(255, int(b)))

    @property
    def hex(self):
        """返回 ``#rrggbb`` 格式的十六进制字符串。"""
        return "#%02x%02x%02x" % (self.r, self.g, self.b)

    @property
    def tuple(self):
        return (self.r, self.g, self.b)

    def __repr__(self):
        return "Color(%d, %d, %d)" % (self.r, self.g, self.b)

    def __eq__(self, other):
        return (
            isinstance(other, Color)
            and (self.r, self.g, self.b) == (other.r, other.g, other.b)
        )

    def __hash__(self):
        return hash((self.r, self.g, self.b))


def to_color(value):
    """把任意合法颜色值统一转换为 tkinter 颜色字符串。

    支持：
    - ``Color`` 实例
    - ``(r, g, b)`` 元组 / 列表（0~255 整数）
    - ``"#rrggbb"`` 十六进制字符串
    - 颜色名称字符串，如 ``"red"``、``"skyblue"``
    """
    if value is None:
        return None
    if isinstance(value, Color):
        return value.hex
    if isinstance(value, (tuple, list)):
        if len(value) < 3:
            raise ValueError("颜色元组至少需要 3 个分量 (r, g, b)")
        r, g, b = (int(c) for c in value[:3])
        return "#%02x%02x%02x" % (max(0, min(255, r)),
                                  max(0, min(255, g)),
                                  max(0, min(255, b)))
    if isinstance(value, str):
        return value
    raise TypeError("无法识别的颜色值: %r（支持 Color / (r,g,b) / '#rrggbb' / 颜色名）" % (value,))


def mix(c1, c2, t=0.5):
    """线性混合两种颜色，t=0 时返回 c1，t=1 时返回 c2。"""
    a = to_color(c1)
    b = to_color(c2)
    if a.startswith("#") and b.startswith("#") and len(a) == 7 and len(b) == 7:
        ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
        br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
        t = max(0.0, min(1.0, float(t)))
        return "#%02x%02x%02x" % (
            int(ar + (br - ar) * t),
            int(ag + (bg - ag) * t),
            int(ab + (bb - ab) * t),
        )
    return a


def random_color():
    """生成一个随机鲜艳颜色。"""
    return Color(random.randint(0, 255),
                 random.randint(0, 255),
                 random.randint(0, 255))


# ---- 常用颜色常量 ----
RED = Color(255, 0, 0)
GREEN = Color(0, 200, 0)
BLUE = Color(30, 120, 255)
YELLOW = Color(255, 220, 0)
ORANGE = Color(255, 140, 0)
PURPLE = Color(150, 60, 200)
PINK = Color(255, 100, 180)
CYAN = Color(0, 220, 220)
LIME = Color(120, 255, 0)
MAGENTA = Color(255, 0, 200)
BROWN = Color(140, 80, 40)
WHITE = Color(255, 255, 255)
BLACK = Color(0, 0, 0)
GRAY = Color(128, 128, 128)
LIGHT_GRAY = Color(200, 200, 200)
DARK_GRAY = Color(60, 60, 60)
NAVY = Color(20, 30, 60)
