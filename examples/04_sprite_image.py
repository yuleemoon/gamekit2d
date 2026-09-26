"""示例 04：图像精灵 / 旋转 / 缩放 / 帧动画。

演示 gamekit 的图像能力（零第三方依赖）：
- 加载 PNG 精灵（assets 由 make_assets.py 生成）
- 缩放（set_scale）、旋转（set_angle）
- 帧动画（Animation，两帧金币循环闪烁）
- 粒子跟随

运行前先执行：python examples/make_assets.py
运行：python examples/04_sprite_image.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamekit import Game, Key, Animation

ASSETS = os.path.join(os.path.dirname(__file__), "assets")


def asset(name):
    return os.path.join(ASSETS, name)


def main():
    game = Game(title="图像精灵 · gamekit", width=720, height=520, fps=60)
    game.bg_color = "#141a24"

    # 玩家：图像精灵，跟随鼠标旋转（像一只"朝向你"的飞船）
    player = game.sprite(asset("player.png"), x=360, y=260)
    player.vx = 220
    player.vy = 170
    player.bounce = 1.0

    # 星星：缩放演示（由小到大往复）
    star = game.sprite(asset("star.png"), x=120, y=100)
    star.bounce = 1.0
    star.vx = 160
    star.vy = 120

    # 金币：两帧动画循环
    coin = game.sprite(asset("coin1.png"), x=600, y=120)
    coin.play([asset("coin1.png"), asset("coin2.png")], fps=4, loop=True)

    game.text("← → 缩放星星 · ↑ ↓ 旋转星星 · 空格暂停玩家",
              x=360, y=500, size=14, color="#8899aa")

    star_dir = [1.0]
    paused = [False]
    saved = [0.0, 0.0]


    @game.on_key(Key.LEFT)
    def star_shrink():
        star.set_scale(max(0.4, star.scale - 0.2))

    @game.on_key(Key.RIGHT)
    def star_grow():
        star.set_scale(min(3.0, star.scale + 0.2))

    @game.on_key(Key.UP)
    def star_turn():
        star.set_angle(star.angle + 45)

    @game.on_key(Key.DOWN)
    def star_turn_back():
        star.set_angle(star.angle - 45)

    @game.on_key(Key.SPACE)
    def toggle_pause():
        paused[0] = not paused[0]
        if paused[0]:
            saved[0], saved[1] = player.vx, player.vy
            player.vx = player.vy = 0
        else:
            player.vx, player.vy = saved

    @game.on_key(Key.ESCAPE)
    def quit_game():
        game.stop()

    if "--selftest" in sys.argv:
        game.after(2.0, game.stop)

    game.run()


if __name__ == "__main__":
    main()
