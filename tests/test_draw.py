"""绘制原语（Line / Polygon / Ellipse / Arc）单元测试（纯逻辑，无需 GUI）。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gamekit.fx.draw import Line, Polygon, Ellipse, Arc


class _FakeGame:
    """模拟 Game 对形状的管理接口。"""
    def __init__(self):
        self._shapes = []

    def _add_shape(self, s):
        if s not in self._shapes:
            self._shapes.append(s)

    def _remove_shape(self, s):
        if s in self._shapes:
            self._shapes.remove(s)


class TestLine(unittest.TestCase):
    def test_center_from_endpoints(self):
        ln = Line(_FakeGame(), 0, 0, 10, 0)
        self.assertEqual((ln.x, ln.y), (5.0, 0.0))
        self.assertEqual((ln.x1, ln.y1, ln.x2, ln.y2), (0.0, 0.0, 10.0, 0.0))

    def test_set_points_updates_center(self):
        ln = Line(_FakeGame(), 0, 0, 10, 0)
        ln.set_points(0, 0, 20, 10)
        self.assertEqual((ln.x, ln.y), (10.0, 5.0))
        self.assertEqual((ln.x1, ln.y1, ln.x2, ln.y2), (0.0, 0.0, 20.0, 10.0))

    def test_velocity_moves_endpoints(self):
        ln = Line(_FakeGame(), 0, 0, 10, 0)
        ln.vx = 10.0
        ln._physics_update(0.1, 0)
        # 中心 5 -> 6，端点整体平移 1
        self.assertEqual(ln.x1, 1.0)
        self.assertEqual(ln.x2, 11.0)

    def test_remove(self):
        g = _FakeGame()
        ln = Line(g, 0, 0, 10, 0)
        g._add_shape(ln)          # 工厂方法之外手动注册
        self.assertEqual(len(g._shapes), 1)
        ln.remove()
        self.assertEqual(len(g._shapes), 0)
        self.assertTrue(ln._removed)


class TestPolygon(unittest.TestCase):
    def test_bbox_and_center(self):
        poly = Polygon(_FakeGame(), [(0, 0), (10, 0), (10, 10), (0, 10)])
        self.assertEqual((poly.left, poly.top, poly.right, poly.bottom),
                         (0.0, 0.0, 10.0, 10.0))
        self.assertEqual((poly.x, poly.y), (5.0, 5.0))

    def test_velocity_moves_points(self):
        poly = Polygon(_FakeGame(), [(0, 0), (10, 0), (10, 10), (0, 10)])
        poly.vx = 5.0
        poly.vy = -2.0
        poly._physics_update(0.1, 0)
        self.assertEqual(poly.points[0], (0.5, -0.2))
        self.assertEqual(poly.x, 5.5)
        self.assertEqual(poly.y, 4.8)

    def test_outline_color(self):
        poly = Polygon(_FakeGame(), [(0, 0), (4, 0), (4, 4)], outline="red")
        self.assertEqual(poly.outline, "red")
        self.assertEqual(poly.color, "white")


class TestEllipse(unittest.TestCase):
    def test_bbox(self):
        el = Ellipse(_FakeGame(), x=100, y=100, width=40, height=20)
        self.assertEqual((el.left, el.top, el.right, el.bottom),
                         (80.0, 90.0, 120.0, 110.0))

    def test_radius_shape(self):
        el = Ellipse(_FakeGame(), x=0, y=0, width=50, height=50)
        self.assertEqual((el.left, el.right), (-25.0, 25.0))


class TestArc(unittest.TestCase):
    def test_attributes(self):
        arc = Arc(_FakeGame(), x=100, y=100, width=40, height=40,
                  start=0, extent=180, color="lime", width_px=3)
        self.assertEqual((arc.start, arc.extent), (0.0, 180.0))
        self.assertEqual(arc.width_px, 3)
        self.assertEqual((arc.left, arc.right), (80.0, 120.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
