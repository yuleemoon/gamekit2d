"""二维向量工具：用于方向、速度、朝向等计算。

只依赖标准库 ``math``，无任何第三方依赖。
"""

import math


class Vec2:
    """一个极简二维向量。

    支持加减、数乘、取负、点积、长度、归一化、距离等常用操作。
    """

    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    # ---- 运算 ----
    def __add__(self, other):
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Vec2(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def __neg__(self):
        return Vec2(-self.x, -self.y)

    def __eq__(self, other):
        return isinstance(other, Vec2) and self.x == other.x and self.y == other.y

    # ---- 常用方法 ----
    def length(self):
        """向量长度。"""
        return math.hypot(self.x, self.y)

    def length_sq(self):
        """向量长度的平方（避免开方，常用于比较）。"""
        return self.x * self.x + self.y * self.y

    def normalized(self):
        """返回同方向的单位向量；零向量返回 Vec2(0, 0)。"""
        n = self.length()
        if n == 0:
            return Vec2(0, 0)
        return Vec2(self.x / n, self.y / n)

    def dot(self, other):
        """点积。"""
        return self.x * other.x + self.y * other.y

    def distance(self, other):
        """到另一个向量的距离。"""
        return math.hypot(self.x - other.x, self.y - other.y)

    def angle(self):
        """返回向量方向角（度，0 表示 +x 方向，逆时针为正）。"""
        return math.degrees(math.atan2(self.y, self.x))

    def rotated(self, degrees):
        """返回旋转后的新向量。"""
        rad = math.radians(degrees)
        c, s = math.cos(rad), math.sin(rad)
        return Vec2(self.x * c - self.y * s, self.x * s + self.y * c)

    # ---- 便捷构造 ----
    @staticmethod
    def from_angle(degrees, magnitude=1.0):
        """从角度（度）和长度构造向量，0 度指向 +x 方向。"""
        rad = math.radians(degrees)
        return Vec2(math.cos(rad) * magnitude, math.sin(rad) * magnitude)

    def __repr__(self):
        return "Vec2(%.2f, %.2f)" % (self.x, self.y)
