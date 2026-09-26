"""粒子系统：爆炸、火花、飘雪等简单特效。"""

import math
import random

from ..utils.color import to_color


class ParticleSystem:
    """一个简单的粒子系统。

    用法：:

        boom = game.particles(x=400, y=300, count=40, speed=(80, 260),
                              colors=("orange", "yellow", "red"))
        boom.burst()        # 爆发一次
        boom.burst(count=80, x=100, y=100)   # 指定位置再次爆发

    粒子会自动衰减（生命周期结束后消失），无需手动清理。
    """

    def __init__(self, game, x=0, y=0, count=30, speed=(50, 180),
                 life=(0.4, 1.5), size=(2, 6), colors=("red", "orange", "yellow"),
                 gravity=120.0, spread=360):
        self.game = game
        self.x = float(x)
        self.y = float(y)
        self.count = int(count)
        self.speed = speed
        self.life = life
        self.size = size
        self.colors = [to_color(c) for c in colors]
        self.gravity = float(gravity)
        self.spread = float(spread)
        self.particles = []   # 每个粒子是一个 dict
        self._removed = False

    # ------------------------------------------------------------------
    def burst(self, x=None, y=None, count=None):
        """一次性爆发粒子。``count`` 缺省用初始数量。"""
        cx = self.x if x is None else x
        cy = self.y if y is None else y
        n = self.count if count is None else int(count)
        for _ in range(n):
            angle = random.uniform(0, 360)
            speed = random.uniform(*self.speed)
            life = random.uniform(*self.life)
            size = random.uniform(*self.size)
            color = random.choice(self.colors)
            self.particles.append({
                "x": float(cx), "y": float(cy),
                "vx": math.cos(math.radians(angle)) * speed,
                "vy": math.sin(math.radians(angle)) * speed,
                "life": life, "max_life": life,
                "size": size, "color": color,
            })
        return self

    def update(self, dt):
        """推进粒子（由 Game 每帧调用）。"""
        for p in list(self.particles):
            p["life"] -= dt
            if p["life"] <= 0:
                self.particles.remove(p)
                continue
            p["vy"] += self.gravity * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt

    def _draw(self, r):
        for p in self.particles:
            alpha = max(0.0, p["life"] / p["max_life"])
            rad = max(0.5, p["size"] * (0.4 + 0.6 * alpha))
            r.draw_oval(p["x"] - rad, p["y"] - rad,
                        p["x"] + rad, p["y"] + rad, p["color"])

    @property
    def alive_count(self):
        return len(self.particles)

    def remove(self):
        if not self._removed:
            self._removed = True
            self.game._remove_particles(self)
        return self
