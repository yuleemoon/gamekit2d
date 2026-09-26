# learn_pygame/backend_demo.py
# 阶段2 验证：同一游戏代码在 GDI 与 tkinter 两个后端各跑一遍。
# 覆盖：精灵(rect/circle)、文字、按钮、进度条、line/polygon/ellipse/arc、
#       按键、鼠标点击、自动 stop。
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\new-chat")

from gamekit import Game, Key


def run_game(backend):
    game = Game("backend demo [%s]" % backend, 480, 320, fps=60, backend=backend)

    # 精灵：方块 + 圆
    box = game.sprite(color="#ff8844", x=60, y=160, width=50, height=50)
    ball = game.sprite(color="yellow", x=240, y=60, width=26, height=26,
                       shape="circle")
    ball.vx, ball.vy = 150, 120

    # 文字
    title = game.text("backend=%s" % backend, 240, 20, size=22, color="white")
    counter = game.text("keys:0", 120, 70, size=16, color="skyblue")

    # 绘制原语
    game.line(0, 280, 480, 280, color="gray", width=1)
    game.polygon([(380, 200), (420, 160), (460, 200), (440, 250), (400, 250)],
                 color="lime")
    game.ellipse(x=90, y=90, width=40, height=26, color="pink")
    game.arc(x=140, y=80, width=46, height=46, start=0, extent=120,
             color="cyan", width_px=3)

    # UI
    bar = game.progress_bar(x=240, y=292, width=220, height=14, value=0,
                            max_value=100)
    btn = game.button("CLICK", x=240, y=130, width=100, height=34,
                      font_size=14)
    clicks = [0]
    btn.on_click = lambda b: clicks.__setitem__(0, clicks[0] + 1)

    # 输入
    key_n = [0]
    @game.on_key(Key.SPACE)
    def on_space():
        key_n[0] += 1
        counter.set_text("keys:%d clicks:%d" % (key_n[0], clicks[0]))

    frame = [0]
    def update(dt):
        box.x += 60 * dt
        if box.right > 480:
            box.x = 10
        ball.x += ball.vx * dt
        ball.y += ball.vy * dt
        if ball.left < 0 or ball.right > 480:
            ball.vx = -ball.vx
        if ball.top < 0 or ball.bottom > 320:
            ball.vy = -ball.vy
        bar.value = (bar.value + 60 * dt) % 100
        frame[0] += 1
        if frame[0] >= 80:
            game.stop()
    game.on_update(update)

    game.run()
    return {"keys": key_n[0], "clicks": clicks[0], "frames": frame[0]}


if __name__ == "__main__":
    for backend in ("gdi", "tk"):
        r = run_game(backend)
        print("[%s] OK  frames=%d keys=%d clicks=%d" % (backend, r["frames"], r["keys"], r["clicks"]))
    print("ALL BACKENDS PASSED")
