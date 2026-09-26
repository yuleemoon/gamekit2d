# 自研 GDI 渲染内核性能基准
# 测纯渲染循环（不含初始化/保存）在不同精灵数下的 FPS。
# 用法: python learn_pygame/bench_gdi.py [精灵数...]

import sys
import time

from gamekit.render import Surface, Window

W, H = 640, 400


def bench(n, duration=2.0):
    win = Window(W, H, "bench %d" % n)
    screen = win.screen
    sprites = []
    for i in range(n):
        s = Surface(20, 20)
        s.fill(((i * 37) % 256, (i * 91) % 256, (i * 53) % 256))
        sprites.append((s, (i * 7) % (W - 20), (i * 13) % (H - 20)))

    frames = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < duration:
        screen.fill((16, 22, 34))
        for s, x, y in sprites:
            s.blit(screen.dc, x, y)
        win.present()
        frames += 1
    dt = time.perf_counter() - t0

    for s, _, _ in sprites:
        s.close()
    win.close()
    return frames / dt


if __name__ == "__main__":
    counts = [int(a) for a in sys.argv[1:]] or [100, 500, 1000, 2000, 5000]
    print("自研 GDI 渲染内核 · 纯渲染 FPS（20x20 精灵，640x400）")
    for n in counts:
        fps = bench(n)
        print("  %5d 个精灵 -> %8.1f FPS" % (n, fps))
