"""碰撞检测单元测试（纯逻辑，无需 GUI / tkinter）。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gamekit.physics.collision import (rect_collide, circle_collide,
                                       point_in_rect, point_in_circle,
                                       distance, collides)


class _Box:
    """测试用的最小矩形对象（模拟 Sprite 的几何接口）。"""
    def __init__(self, x, y, w, h, shape="rect"):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.shape = shape


class TestRectCollision(unittest.TestCase):
    def test_overlap_center(self):
        a = _Box(100, 100, 40, 40)
        b = _Box(110, 110, 40, 40)
        self.assertTrue(rect_collide(a, b))

    def test_no_overlap_far(self):
        a = _Box(100, 100, 40, 40)
        b = _Box(300, 300, 40, 40)
        self.assertFalse(rect_collide(a, b))

    def test_edge_touching_is_collision(self):
        # 恰好边贴边：AABB 用 < 比较，边贴边不算重叠（严格小于）
        a = _Box(100, 100, 40, 40)   # 左 80 右 120
        b = _Box(140, 100, 40, 40)   # 左 120 右 160
        self.assertFalse(rect_collide(a, b))

    def test_partial_overlap(self):
        a = _Box(100, 100, 100, 40)
        b = _Box(140, 100, 40, 100)
        self.assertTrue(rect_collide(a, b))

    def test_contained(self):
        a = _Box(100, 100, 100, 100)
        b = _Box(100, 100, 20, 20)
        self.assertTrue(rect_collide(a, b))


class TestCircleCollision(unittest.TestCase):
    def test_overlap(self):
        a = _Box(100, 100, 40, 40, "circle")   # r=20
        b = _Box(130, 100, 40, 40, "circle")   # r=20, 相距 30 < 40
        self.assertTrue(circle_collide(a, b))

    def test_touching(self):
        a = _Box(100, 100, 40, 40, "circle")   # r=20
        b = _Box(140, 100, 40, 40, "circle")   # r=20, 相距 40 = r+r
        self.assertTrue(circle_collide(a, b))

    def test_far(self):
        a = _Box(100, 100, 40, 40, "circle")
        b = _Box(200, 100, 40, 40, "circle")   # 相距 100 > 40
        self.assertFalse(circle_collide(a, b))


class TestPointAndDistance(unittest.TestCase):
    def test_point_in_rect(self):
        a = _Box(100, 100, 40, 40)
        self.assertTrue(point_in_rect(100, 100, a))
        self.assertTrue(point_in_rect(90, 95, a))
        self.assertFalse(point_in_rect(200, 200, a))

    def test_point_in_circle(self):
        a = _Box(100, 100, 40, 40, "circle")
        self.assertTrue(point_in_circle(100, 100, a))
        self.assertTrue(point_in_circle(115, 100, a))
        self.assertFalse(point_in_circle(150, 100, a))

    def test_distance(self):
        a = _Box(0, 0, 10, 10)
        b = _Box(3, 4, 10, 10)
        self.assertAlmostEqual(distance(a, b), 5.0, places=6)


class TestDispatch(unittest.TestCase):
    def test_circle_vs_circle(self):
        a = _Box(100, 100, 40, 40, "circle")
        b = _Box(130, 100, 40, 40, "circle")
        self.assertTrue(collides(a, b))

    def test_rect_vs_rect(self):
        a = _Box(100, 100, 40, 40)
        b = _Box(110, 110, 40, 40)
        self.assertTrue(collides(a, b))

    def test_mixed_uses_rect(self):
        a = _Box(100, 100, 40, 40, "circle")
        b = _Box(130, 100, 40, 40, "rect")
        # 混合时退化为矩形检测：重叠 → True
        self.assertTrue(collides(a, b))


if __name__ == "__main__":
    unittest.main(verbosity=2)
