# learn_pygame/bench_camera.py
# Camera + 视口裁剪基准：4000 个精灵分布在 3200x2400 的大地图里，
# 相机在地图上扫过。只画屏幕内的精灵。
import sys, time
sys.path.insert(0, r"C:\Users\Administrator\Desktop\new-chat")
from gamekit import Game

W, H = 640, 400
WORLD_W, WORLD_H = 3200, 2400


def run():
    g = Game("camera bench", W, H, fps=999, backend="gdi")
    import random
    random.seed(11)
    sprites = []
    for i in range(4000):
        c = "#%02x%02x%02x" % ((i*37) % 256, (i*91) % 256, (i*53) % 256)
        s = g.sprite(color=c,
                     x=random.randint(0, WORLD_W-32),
                     y=random.randint(0, WORLD_H-32),
                     width=32, height=32)
        sprites.append(s)
    frames = [0]
    t0 = time.perf_counter()

    def update(dt):
        frames[0] += 1
        # 相机在世界里来回扫
        g.camera_x = int((WORLD_W - W) / 2 + (WORLD_W - W) / 2
                         * __import__("math").sin(frames[0] / 60.0))
        g.camera_y = int((WORLD_H - H) / 2 + (WORLD_H - H) / 2
                         * __import__("math").cos(frames[0] / 90.0))
        if time.perf_counter() - t0 >= 3.0:
            g.stop()

    g.on_update(update)
    g.run()
    return frames[0] / (time.perf_counter() - t0)


if __name__ == "__main__":
    fps = run()
    print("Camera + culling: 4000 精灵分布在 3200x2400，相机扫图")
    print("  FPS: %.1f  (对比：4000 个全画无 culling = ~38 FPS)" % fps)
