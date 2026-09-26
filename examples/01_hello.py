"""示例 01：Hello GameKit —— 最小可运行游戏。

一个反弹的小球 + 一行文字。演示极简 API：
创建 Game、创建精灵、注册按键与更新回调、run() 开跑。
运行：python examples/01_hello.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamekit import Game, Key

game = Game(title="Hello GameKit", width=640, height=480, fps=60)

# 一个黄色圆形精灵，设置速度并开启边缘反弹
ball = game.sprite(color="#ffcc00", x=320, y=240, width=40, height=40, shape="circle")
ball.vx = 220
ball.vy = 160
ball.bounce = 1.0

hint = game.text("方向键改变球色 · 空格暂停 · ESC 退出",
                 x=320, y=450, size=14, color="#888888")

paused = [False]
saved = [0.0, 0.0]

colors = ["#ffcc00", "#4ac0f0", "#ff6b6b", "#6bff9c", "#c86bff"]
idx = [0]


@game.on_key(Key.LEFT)
def prev_color():
    idx[0] = (idx[0] - 1) % len(colors)
    ball.set_color(colors[idx[0]])


@game.on_key(Key.RIGHT)
def next_color():
    idx[0] = (idx[0] + 1) % len(colors)
    ball.set_color(colors[idx[0]])


@game.on_key(Key.SPACE)
def toggle_pause():
    paused[0] = not paused[0]
    if paused[0]:
        saved[0], saved[1] = ball.vx, ball.vy
        ball.vx = ball.vy = 0
    else:
        ball.vx, ball.vy = saved


@game.on_key(Key.ESCAPE)
def quit_game():
    game.stop()


if "--selftest" in sys.argv:
    game.after(2.0, game.stop)   # 自动化验证：2 秒后自动关闭

game.run()
print("Hello GameKit 运行结束")
