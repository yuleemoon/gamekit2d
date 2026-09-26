# 阶段1验证 demo：自研 GDI 渲染内核
# 用 gamekit.render 的 Surface + Window 做一个小场景：
# 彩块反弹 + 粒子闪烁，跑 150 帧，保存 BMP 截图，验证自研内核能画能动。
#
# 全程零第三方依赖（ctypes 直接调系统 GDI）。

import random
import struct
import time

from gamekit.render import Surface, Window

W, H = 640, 400


def save_bmp(surface, path):
    """把 Surface 的 BGRA 像素写成 BMP 文件（自研内核的截图验证）。
    只依赖标准库 struct。"""
    w, h = surface.width, surface.height
    row_size = w * 4
    pad = (4 - row_size % 4) % 4
    data = bytearray()
    for y in range(h - 1, -1, -1):      # BMP 是 bottom-up
        for x in range(w):
            r, g, b, a = surface.get_at(x, y)
            data += bytes((b, g, r, 255))
        data += bytes(pad)

    file_size = 14 + 40 + len(data)
    header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 32, 0,
                       len(data), 0, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(header + info + bytes(data))


def main():
    random.seed(7)
    win = Window(W, H, "gamekit render kernel demo")
    screen = win.screen

    # 造精灵：每个是一块像素缓冲（相当于 pygame.Surface）
    sprites = []
    for i in range(24):
        size = random.randint(14, 40)
        s = Surface(size, size)
        r, g, b = random.randint(60, 255), random.randint(60, 255), random.randint(60, 255)
        s.fill((r, g, b))
        # 画个边框让移动更明显
        for k in range(size):
            s.set_at(k, 0, (255, 255, 255))
            s.set_at(k, size - 1, (255, 255, 255))
            s.set_at(0, k, (255, 255, 255))
            s.set_at(size - 1, k, (255, 255, 255))
        sprites.append({
            "surf": s, "x": random.uniform(0, W - size),
            "y": random.uniform(0, H - size),
            "vx": random.uniform(-160, 160), "vy": random.uniform(-160, 160),
            "size": size,
        })

    # 一个小粒子：闪烁的圆点（用像素循环画）
    dot = Surface(12, 12)
    for yy in range(12):
        for xx in range(12):
            dx, dy = xx - 6, yy - 6
            if dx * dx + dy * dy <= 30:
                dot.set_at(xx, yy, (255, 220, 80))

    frames = 0
    fps_meas = 0.0
    t0 = time.perf_counter()

    while win.poll_events():
        # 清屏
        screen.fill((16, 22, 34))

        # 更新 + 绘制精灵（整块 blit，纯位块传送）
        for sp in sprites:
            sp["x"] += sp["vx"] / 60.0
            sp["y"] += sp["vy"] / 60.0
            if sp["x"] < 0 or sp["x"] + sp["size"] > W:
                sp["vx"] = -sp["vx"]
            if sp["y"] < 0 or sp["y"] + sp["size"] > H:
                sp["vy"] = -sp["vy"]
            sp["surf"].blit(screen.dc, int(sp["x"]), int(sp["y"]))

        # 粒子
        dot.blit(screen.dc, (frames * 13) % (W - 12), 30 + (frames % 40))

        win.present()          # 翻屏 = pygame.display.flip()
        frames += 1
        if frames >= 150:
            break

    dt = time.perf_counter() - t0
    fps_meas = frames / dt

    save_bmp(screen, "render_demo_result.bmp")
    print("frames:", frames, "| avg fps (150 frames incl. init):", round(fps_meas, 1))
    print("saved render_demo_result.bmp")

    for sp in sprites:
        sp["surf"].close()
    dot.close()
    win.close()


if __name__ == "__main__":
    main()
