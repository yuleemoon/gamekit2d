# learn_pygame/bench_static.py
# 静态精灵不重画基准：大量 static 精灵 + 少数 dynamic 移动精灵。
# 对比 dirty=False（每帧全画）vs dirty=True（静态精灵只画一次）。
import sys, time
sys.path.insert(0, r"C:\Users\Administrator\Desktop\new-chat")
from gamekit import Game

W, H = 640, 400


def run(n_static=400, n_mover=8, dirty=False, duration=2.0):
    g = Game("static bench", W, H, fps=999, backend="gdi", dirty=dirty)
    import random
    random.seed(3)
    for i in range(n_static):
        c = "#%02x%02x%02x" % ((i*37) % 256, (i*91) % 256, (i*53) % 256)
        g.sprite(color=c, x=(i*7) % (W-32), y=(i*13) % (H-32),
                 width=32, height=32, static=True)
    movers = [g.sprite(color="yellow", x=100+i*40, y=200, width=24, height=24)
              for i in range(n_mover)]
    frames = [0]
    t0 = time.perf_counter()

    def update(dt):
        frames[0] += 1
        for s in movers:
            s.x += 2.0
            if s.x > W:
                s.x = -32
        if time.perf_counter() - t0 >= duration:
            g.stop()

    g.on_update(update)
    g.run()
    return frames[0] / (time.perf_counter() - t0)


if __name__ == "__main__":
    print("静态精灵基准 · 400 static + 8 dynamic · GDI")
    off = run(400, 8, dirty=False)
    on = run(400, 8, dirty=True)
    print("  每帧全画    dirty=False: %8.1f FPS" % off)
    print("  静态只画一次 dirty=True : %8.1f FPS" % on)
    print("  倍率: %.2fx" % (on / off))
    print()
    print("=== 4000 全动（不标记 static）===")
    off2 = run(0, 4000, dirty=False)
    on2 = run(0, 4000, dirty=True)
    print("  dirty=False: %8.1f FPS" % off2)
    print("  dirty=True : %8.1f FPS" % on2)
