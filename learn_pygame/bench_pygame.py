# pygame 对照基准：同一场景（20x20 精灵，640x400）测纯渲染 FPS
# 用法: python learn_pygame/bench_pygame.py [精灵数...]

import sys
import time

import pygame

W, H = 640, 400


def bench(n, duration=2.0):
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    sprites = []
    for i in range(n):
        s = pygame.Surface((20, 20))
        s.fill(((i * 37) % 256, (i * 91) % 256, (i * 53) % 256))
        sprites.append((s, (i * 7) % (W - 20), (i * 13) % (H - 20)))

    frames = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < duration:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return 0.0
        screen.fill((16, 22, 34))
        for s, x, y in sprites:
            screen.blit(s, (x, y))
        pygame.display.flip()
        frames += 1
    dt = time.perf_counter() - t0
    pygame.quit()
    return frames / dt


if __name__ == "__main__":
    counts = [int(a) for a in sys.argv[1:]] or [100, 500, 1000, 2000, 5000]
    print("pygame-ce 对照 · 纯渲染 FPS（20x20 精灵，640x400）")
    for n in counts:
        print("  %5d 个精灵 -> %8.1f FPS" % (n, bench(n)))
