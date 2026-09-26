"""GUI 冒烟测试：启动一个真实的 Game，自动运行若干帧后退出。

用途：验证核心渲染 / 事件 / 物理 / 场景 / 粒子 / 按钮全流程可跑通。
运行：python tests/run_selftest.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import gamekit
from gamekit import Game, Scene, Key, pixel_collide


def main():
    game = Game(title="gamekit selftest", width=640, height=480, fps=60)

    # ---- 精灵 ----
    player = game.sprite(color="red", x=100, y=100, width=50, height=50)
    player.vx = 120
    player.vy = 60
    player.bounce = 1.0           # 撞边反弹

    coin = game.sprite(color="gold", x=150, y=100, width=30, height=30,
                       shape="circle", tag="coin")
    coin.vx = 0

    # ---- 物理 ----
    ball = game.sprite(color="cyan", x=320, y=240, width=20, height=20,
                       shape="circle")
    ball.gravity_scale = 1.0      # 受全局重力影响
    ball.bounce = 0.9
    game.gravity = 300

    # ---- 文本 / 按钮 / 进度条 ----
    info = game.text("selftest", x=320, y=30, size=18)
    bar = game.progress_bar(x=320, y=60, width=300, height=18, value=0, max_value=100)
    game.button("Quit", x=320, y=440, width=120, height=40, on_click=lambda b: game.stop())

    # ---- 粒子 ----
    ps = game.particles(x=320, y=240, count=20, colors=("red", "orange", "yellow"))
    ps.burst()

    # ---- 绘制原语（pygame.draw 等价）----
    game.line(x1=20, y1=400, x2=200, y2=400, color="white", width=3)
    game.polygon([(300, 400), (330, 360), (360, 400)], color="violet")
    game.ellipse(x=440, y=400, width=80, height=40, color="skyblue")
    game.arc(x=560, y=400, width=60, height=60, start=0, extent=270,
             color="lime", width_px=3)

    # ---- 图像精灵：翻转 / 保存 / 像素碰撞 ----
    asset = os.path.join(os.path.dirname(__file__), "..", "examples", "assets", "player.png")
    img_a = None
    img_b = None
    if os.path.exists(asset):
        img_a = game.sprite(asset, x=60, y=320)
        img_a.flip(horizontal=True)
        img_b = game.sprite(asset, x=90, y=320)   # 与 img_a 重叠
        img_far = game.sprite(asset, x=560, y=300)
        img_a.save_image(os.path.join(os.path.dirname(__file__), "..", "_flip_test.ppm"))
        assert pixel_collide(img_a, img_b), "重叠图像精灵应发生像素碰撞"
        assert not pixel_collide(img_a, img_far), "分离图像精灵不应碰撞"

    # ---- 事件 ----
    @game.on_key(Key.ESCAPE)
    def quit_game():
        game.stop()

    @game.on_key(Key.SPACE)
    def burst():
        ps.burst(count=30)

    @game.on_key("a")
    def hide_player():
        player.hide()

    @game.on_key("s")
    def show_player():
        player.show()

    frame_count = [0]
    render_checked = [False]

    @game.on_update
    def tick(dt):
        frame_count[0] += 1
        bar.set_value(frame_count[0] % 100)
        info.set("frame %d  sprites=%d  dt=%.3f" % (
            frame_count[0], len(game.sprites), game.dt))

        # 第 30 帧验证渲染管线确实画出了内容
        if frame_count[0] == 30 and not render_checked[0]:
            render_checked[0] = True
            items = len(game.canvas.find_all())
            assert items > 0, "canvas 没有绘制任何内容，渲染管线异常"
            all_items = game.canvas.find_all()
            kinds = {game.canvas.type(i) for i in all_items}
            assert "line" in kinds, "Line 原语没有绘制"
            assert "polygon" in kinds, "Polygon 原语没有绘制"
            assert "oval" in kinds, "Ellipse / Arc 原语没有绘制"
            print("渲染验证: canvas item 数量 = %d, 类型 = %s" % (items, sorted(kinds)))
            game.canvas.postscript(file="selftest_render.ps")

        if frame_count[0] >= 120:
            game.stop()

    # ---- 碰撞回调 ----
    got = []

    @game.on_collide(player, "coin")
    def collect(p, c):
        got.append(1)
        c.remove()

    game.run()

    print("selftest OK: 运行了 %d 帧" % frame_count[0])
    print("碰撞回调触发次数:", len(got))
    assert frame_count[0] >= 100, "帧数不足，主循环可能异常"
    for tmp in ("selftest_render.ps", os.path.join(os.path.dirname(__file__), "..", "_flip_test.ppm")):
        if os.path.exists(tmp):
            os.remove(tmp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
