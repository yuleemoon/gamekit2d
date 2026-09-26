"""生成示例用图像资产（PNG）。

零第三方依赖：直接用 tkinter 的 PhotoImage 逐像素绘制并写为 PNG。
运行一次即可生成 examples/assets/ 下的图片：
    python examples/make_assets.py
"""

import os
import tkinter as tk

OUT_DIR = os.path.join(os.path.dirname(__file__), "assets")


def fill_rect(img, x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(img.height(), y1) + 1):
        for x in range(max(0, x0), min(img.width(), x1) + 1):
            img.put(color, to=(x, y))


def fill_circle(img, cx, cy, r, color):
    r2 = r * r
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - r), int(cx + r) + 1):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy <= r2 and 0 <= x < img.width() and 0 <= y < img.height():
                img.put(color, to=(x, y))


def fill_diamond(img, cx, cy, rx, ry, color):
    for y in range(int(cy - ry), int(cy + ry) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            if abs(x - cx) / rx + abs(y - cy) / ry <= 1 and \
               0 <= x < img.width() and 0 <= y < img.height():
                img.put(color, to=(x, y))


def save(img, name):
    path = os.path.join(OUT_DIR, name)
    img.write(path, format="png")
    print("生成:", path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    root = tk.Tk()
    root.withdraw()

    # 玩家：蓝色圆 + 白色描边
    img = tk.PhotoImage(width=64, height=64)
    fill_circle(img, 32, 32, 30, "#e8e8e8")
    fill_circle(img, 32, 32, 26, "#4a90d9")
    fill_circle(img, 26, 26, 6, "#ffffff")
    fill_circle(img, 38, 26, 6, "#ffffff")
    save(img, "player.png")

    # 金币：金色圆（两帧用于动画演示）
    for name, gold in (("coin1.png", "#f6c344"), ("coin2.png", "#e8a020")):
        img = tk.PhotoImage(width=48, height=48)
        fill_circle(img, 24, 24, 22, "#8a5a00")
        fill_circle(img, 24, 24, 19, gold)
        fill_circle(img, 24, 24, 8, "#ffe9a8")
        save(img, name)

    # 星星：黄色菱形 + 橙色描边
    img = tk.PhotoImage(width=56, height=56)
    fill_diamond(img, 28, 28, 26, 26, "#c96a00")
    fill_diamond(img, 28, 28, 21, 21, "#ffd93d")
    save(img, "star.png")

    root.destroy()
    print("全部完成。")


if __name__ == "__main__":
    main()
