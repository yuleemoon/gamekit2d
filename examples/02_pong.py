"""示例 02：双人乒乓球 Pong。

演示：键盘持续输入（on_key_hold / is_key_down）、矩形与圆形碰撞、
自定义碰撞反弹逻辑、实时文本计分。
运行：python examples/02_pong.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamekit import Game, Key

W, H = 800, 500
SPEED = 340

game = Game(title="Pong 乒乓球", width=W, height=H, fps=60)
game.bg_color = "#0e1116"

# 两个挡板（纯色矩形）
left = game.sprite(color="white", x=40, y=H // 2, width=16, height=90)
right = game.sprite(color="white", x=W - 40, y=H // 2, width=16, height=90)

# 球（圆形）
ball = game.sprite(color="#ffcc00", x=W // 2, y=H // 2, width=16, height=16, shape="circle")

# 中线
game.text("|", x=W // 2, y=H // 2, size=14, color="#333333")

score_l = [0]
score_r = [0]
score_text = game.text("0 : 0", x=W // 2, y=34, size=40, bold=True)


def reset_ball(direction):
    ball.move_to(W // 2, H // 2)
    ball.vx = direction * 280
    ball.vy = (0 if score_l[0] + score_r[0] == 0 else 160)  # 开场水平直发


@game.on_update
def tick(dt):
    # 挡板控制（持续按住）
    left.vy = -SPEED if game.is_key_down("w") else (SPEED if game.is_key_down("s") else 0)
    right.vy = -SPEED if game.is_key_down(Key.UP) else (SPEED if game.is_key_down(Key.DOWN) else 0)

    # 上下墙反弹
    if ball.y - 8 < 0:
        ball.y = 8
        ball.vy = abs(ball.vy)
    elif ball.y + 8 > H:
        ball.y = H - 8
        ball.vy = -abs(ball.vy)

    # 出界得分
    if ball.x < -12:
        score_r[0] += 1
        reset_ball(1)
    elif ball.x > W + 12:
        score_l[0] += 1
        reset_ball(-1)
    score_text.set("%d : %d" % (score_l[0], score_r[0]))


@game.on_collide(ball, left)
def hit_left(b, p):
    if b.vx < 0:
        b.vx = abs(b.vx)
        b.vy += (b.y - p.y) * 3.5      # 击打位置影响球路


@game.on_collide(ball, right)
def hit_right(b, p):
    if b.vx > 0:
        b.vx = -abs(b.vx)
        b.vy += (b.y - p.y) * 3.5


@game.on_key(Key.ESCAPE)
def quit_game():
    game.stop()


if "--selftest" in sys.argv:
    game.after(2.0, game.stop)

game.run()
