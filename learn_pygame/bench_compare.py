# learn_pygame/bench_compare.py
# 标准性能基准：同一场景（N 个 32x32 彩色矩形精灵）分别跑 GDI / tk 后端。
# 用 Game 完整路径（精灵系统 + 主循环），与真实使用一致，结果可复现。
# 用法: python learn_pygame/bench_compare.py [精灵数...]
import sys
import time

sys.path.insert(0, r"C:\Users\Administrator\Desktop\new-chat")
from gamekit import Game

W, H = 640, 400


def bench(backend, n, duration=2.0):
    g = Game("bench %s %d" % (backend, n), W, H, fps=999, backend=backend)
    for i in range(n):
        c = "#%02x%02x%02x" % ((i * 37) % 256, (i * 91) % 256, (i * 53) % 256)
        g.sprite(color=c, x=(i * 7) % (W - 32), y=(i * 13) % (H - 32),
                 width=32, height=32)
    frames = [0]
    t0 = time.perf_counter()

    def update(dt):
        frames[0] += 1
        if time.perf_counter() - t0 >= duration:
            g.stop()

    g.on_update(update)
    g.run()
    return frames[0] / (time.perf_counter() - t0)


if __name__ == "__main__":
    counts = [int(a) for a in sys.argv[1:]] or [100, 500, 1000, 2000]
    print("gamekit 标准基准 · 32x32 彩色矩形精灵 · 640x400 · 2s")
    print("%8s %12s %12s %8s" % ("精灵数", "GDI FPS", "tk FPS", "倍率"))
    for n in counts:
        fg = bench("gdi", n)
        ft = bench("tk", n)
        print("%8d %12.1f %12.1f %7.2fx" % (n, fg, ft, fg / ft if ft else 0))
