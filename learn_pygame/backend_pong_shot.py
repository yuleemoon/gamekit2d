# learn_pygame/backend_pong_shot.py
# 阶段2 验证：用 GDI 后端跑一段简化 pong，渲染到第 90 帧时
# 从 renderer 的后台 Surface 存 BMP 截图，验证画面正确。
import os
import struct
import sys

sys.path.insert(0, r"C:\Users\Administrator\Desktop\new-chat")

from gamekit import Game

W, H = 480, 300
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gdi_pong.bmp")


def save_bmp(surface, path):
    w, h = surface.width, surface.height
    row_size = w * 4
    pad = (4 - row_size % 4) % 4
    data = bytearray()
    for y in range(h - 1, -1, -1):
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


game = Game("gdi pong shot", W, H, fps=60, backend="gdi")
game.bg_color = "#0e1116"

left = game.sprite(color="white", x=40, y=H // 2, width=16, height=90)
right = game.sprite(color="white", x=W - 40, y=H // 2, width=16, height=90)
ball = game.sprite(color="#ffcc00", x=W // 2, y=H // 2, width=16, height=16,
                   shape="circle")
score = game.text("3 : 5", x=W // 2, y=30, size=32, bold=True)
game.ellipse(x=W // 2, y=H // 2, width=60, height=60, color="#222a36")

ball.vx, ball.vy = 220, 150
f = [0]


def tick(dt):
    ball.x += ball.vx * dt
    ball.y += ball.vy * dt
    if ball.y - 8 < 0 or ball.y + 8 > H:
        ball.vy = -ball.vy
    if ball.x - 8 < 0 or ball.x + 8 > W:
        ball.vx = -ball.vx
    f[0] += 1
    if f[0] == 90:
        save_bmp(game._renderer._screen, OUT)
        print("saved", OUT)
        game.stop()


game.on_update(tick)
game.run()
print("frames:", f[0])
