# learn_pygame/bench_dirty.py
# 脏矩形局部更新基准：同一场景下对比 dirty=False（整屏清屏）vs dirty=True（局部恢复）。
# 场景 A：全动（1000 个精灵每个每帧移动）
# 场景 B：少动（400 个静态精灵 + 8 个移动）
import sys
import time

sys.path.insert(0, r"C:\Users\Administrator\Desktop\new-chat")
from gamekit import Game

W, H = 640, 400


def run(scene, n_move, duration=2.0, dirty=False):
    g = Game("bench", W, H, fps=999, backend="gdi", dirty=dirty)
    import random
    random.seed(7)
    movers = []
    if scene == "all":
        for i in range(n_move):
            c = "#%02x%02x%02x" % ((i * 37) % 256, (i * 91) % 256, (i * 53) % 256)
            s = g.sprite(color=c, x=(i * 7) % (W - 32), y=(i * 13) % (H - 32),
                         width=32, height=32)
            movers.append(s)
    else:
        # 静态背景精灵（不动）
        for i in range(400):
            c = "#%02x%02x%02x" % ((i * 37) % 256, (i * 91) % 256, (i * 53) % 256)
            g.sprite(color=c, x=(i * 7) % (W - 32), y=(i * 13) % (H - 32),
                     width=32, height=32)
        # 少数移动精灵
        for i in range(n_move):
            movers.append(g.sprite(color="yellow", x=100 + i * 40, y=200,
                                   width=24, height=24))

    frames = [0]
    t0 = time.perf_counter()

    def update(dt):
        frames[0] += 1
        for s in movers:
            s.x += 1.5
            if s.x > W:
                s.x = -32
        if time.perf_counter() - t0 >= duration:
            g.stop()

    g.on_update(update)
    g.run()
    return frames[0] / (time.perf_counter() - t0)


if __name__ == "__main__":
    print("脏矩形基准 · GDI 后端 · 640x400 · 2s")
    print()
    print("=== 场景 A：1000 个精灵全动 ===")
    off = run("all", 1000, dirty=False)
    on = run("all", 1000, dirty=True)
    print("  整屏清屏 dirty=False: %8.1f FPS" % off)
    print("  局部恢复 dirty=True : %8.1f FPS" % on)
    print("  倍率: %.2fx (1.0=持平, <1=dirty 更慢)" % (on / off))
    print()
    print("=== 场景 B：400 静态 + 8 个移动 ===")
    off2 = run("static", 8, dirty=False)
    on2 = run("static", 8, dirty=True)
    print("  整屏清屏 dirty=False: %8.1f FPS" % off2)
    print("  局部恢复 dirty=True : %8.1f FPS" % on2)
    print("  倍率: %.2fx" % (on2 / off2))
