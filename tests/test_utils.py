"""颜色 / 向量 / 按键标准化 单元测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gamekit.utils.color import Color, to_color, mix
from gamekit.utils.vector import Vec2
from gamekit.core.keys import Key, normalize


class TestColor(unittest.TestCase):
    def test_hex(self):
        self.assertEqual(Color(255, 0, 0).hex, "#ff0000")
        self.assertEqual(Color(0, 128, 255).hex, "#0080ff")

    def test_clamp(self):
        self.assertEqual(Color(300, -5, 128).tuple, (255, 0, 128))

    def test_to_color(self):
        self.assertEqual(to_color(Color(1, 2, 3)), "#010203")
        self.assertEqual(to_color((255, 0, 0)), "#ff0000")
        self.assertEqual(to_color([0, 255, 0]), "#00ff00")
        self.assertEqual(to_color("red"), "red")
        self.assertIsNone(to_color(None))

    def test_mix(self):
        # 红 -> 蓝 的中间是 #7f007f（非严格，只验证边界）
        self.assertEqual(mix("#000000", "#ffffff", 0.0), "#000000")
        self.assertEqual(mix("#000000", "#ffffff", 1.0), "#ffffff")
        mid = mix("#000000", "#ffffff", 0.5)
        self.assertEqual(mid, "#7f7f7f")


class TestVec2(unittest.TestCase):
    def test_add_sub(self):
        v = Vec2(1, 2) + Vec2(3, 4)
        self.assertEqual((v.x, v.y), (4.0, 6.0))
        v = Vec2(5, 5) - Vec2(1, 2)
        self.assertEqual((v.x, v.y), (4.0, 3.0))

    def test_scale(self):
        v = Vec2(2, 3) * 2
        self.assertEqual((v.x, v.y), (4.0, 6.0))

    def test_length(self):
        self.assertAlmostEqual(Vec2(3, 4).length(), 5.0)

    def test_normalized(self):
        n = Vec2(3, 4).normalized()
        self.assertAlmostEqual(n.length(), 1.0)
        self.assertAlmostEqual(n.x, 0.6)

    def test_zero_normalized(self):
        n = Vec2(0, 0).normalized()
        self.assertEqual((n.x, n.y), (0.0, 0.0))

    def test_dot(self):
        self.assertEqual(Vec2(1, 0).dot(Vec2(0, 1)), 0.0)
        self.assertEqual(Vec2(1, 2).dot(Vec2(3, 4)), 11.0)

    def test_distance(self):
        self.assertAlmostEqual(Vec2(0, 0).distance(Vec2(3, 4)), 5.0)

    def test_from_angle(self):
        v = Vec2.from_angle(0, 2)
        self.assertAlmostEqual(v.x, 2.0, places=6)
        self.assertAlmostEqual(v.y, 0.0, places=6)
        v = Vec2.from_angle(90, 1)
        self.assertAlmostEqual(v.x, 0.0, places=6)
        self.assertAlmostEqual(v.y, 1.0, places=6)


class TestKeys(unittest.TestCase):
    def test_normalize_aliases(self):
        self.assertEqual(normalize("space"), "space")
        self.assertEqual(normalize("SPACE"), "space")
        self.assertEqual(normalize(Key.SPACE), "space")
        self.assertEqual(normalize("up"), "Up")
        self.assertEqual(normalize("UP"), "Up")
        self.assertEqual(normalize("enter"), "Return")
        self.assertEqual(normalize("esc"), "Escape")
        self.assertEqual(normalize("ctrl"), "Control_L")

    def test_normalize_letters(self):
        self.assertEqual(normalize("a"), "a")
        self.assertEqual(normalize("A"), "a")
        self.assertEqual(normalize(Key.W), "w")
        self.assertEqual(normalize("F5"), "F5")
        self.assertEqual(normalize("f5"), "F5")
        self.assertEqual(normalize("3"), "3")

    def test_key_dynamic_attr(self):
        self.assertEqual(Key.Z, "z")
        self.assertEqual(Key.F9, "F9")
        self.assertEqual(Key.Q, "q")


if __name__ == "__main__":
    unittest.main(verbosity=2)
