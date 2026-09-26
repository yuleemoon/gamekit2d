"""碰撞检测：矩形（AABB）与圆形碰撞，全部手写实现。"""

import math


def rect_collide(a, b):
    """两个精灵的矩形（AABB）碰撞检测。

    :param a: 任意具有 ``x/y/width/height`` 的对象
    :param b: 同上
    :return: 是否重叠
    """
    return (
        a.x - a.width / 2 < b.x + b.width / 2
        and a.x + a.width / 2 > b.x - b.width / 2
        and a.y - a.height / 2 < b.y + b.height / 2
        and a.y + a.height / 2 > b.y - b.height / 2
    )


def circle_collide(a, b):
    """两个精灵的圆形碰撞检测（半径取宽高较小者的一半）。"""
    ra = min(a.width, a.height) / 2
    rb = min(b.width, b.height) / 2
    dx = a.x - b.x
    dy = a.y - b.y
    r = ra + rb
    return dx * dx + dy * dy <= r * r


def point_in_rect(x, y, obj):
    """点 (x, y) 是否在对象的矩形内。"""
    return (
        obj.x - obj.width / 2 <= x <= obj.x + obj.width / 2
        and obj.y - obj.height / 2 <= y <= obj.y + obj.height / 2
    )


def point_in_circle(x, y, obj):
    """点 (x, y) 是否在对象的圆形内。"""
    r = min(obj.width, obj.height) / 2
    dx = x - obj.x
    dy = y - obj.y
    return dx * dx + dy * dy <= r * r


def distance(a, b):
    """两个对象中心的距离。"""
    return math.hypot(a.x - b.x, a.y - b.y)


def collides(a, b):
    """通用碰撞分派：两个圆 → 圆形检测，其余 → 矩形检测。"""
    sa = getattr(a, "shape", None)
    sb = getattr(b, "shape", None)
    if sa == "circle" and sb == "circle":
        return circle_collide(a, b)
    return rect_collide(a, b)


def pixel_collide(a, b):
    """像素级碰撞（等价于 pygame.mask 的粗略版本）。

    对两个图像精灵，在重叠区域内逐像素比较透明度：只要有一个像素对
    （各自图像上都非透明）重叠，就判定碰撞。透明像素不会触发碰撞，
    比矩形碰撞更精确。

    - 任一对象没有图像，或图像不支持透明检测时，自动退化为矩形碰撞。
    - 纯色精灵直接走矩形碰撞。

    :param a, b: 两个 Sprite
    """
    pa = getattr(a, "_photo", None)
    pb = getattr(b, "_photo", None)
    if pa is None or pb is None:
        return rect_collide(a, b)
    # 重叠区域（像素级 bbox）
    ox0 = max(int(a.left), int(b.left))
    oy0 = max(int(a.top), int(b.top))
    ox1 = min(int(a.right), int(b.right))
    oy1 = min(int(a.bottom), int(b.bottom))
    if ox1 <= ox0 or oy1 <= oy0:
        return False
    has_a = hasattr(pa, "transparency_get")
    has_b = hasattr(pb, "transparency_get")
    if not (has_a and has_b):
        return rect_collide(a, b)
    for py in range(oy0, oy1):
        for px in range(ox0, ox1):
            sax = px - int(a.left)
            say = py - int(a.top)
            sbx = px - int(b.left)
            sby = py - int(b.top)
            if 0 <= sax < a.width and 0 <= say < a.height \
               and 0 <= sbx < b.width and 0 <= sby < b.height:
                if (not pa.transparency_get(sax, say)
                        and not pb.transparency_get(sbx, sby)):
                    return True
    return False
