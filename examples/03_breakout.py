"""示例 03：打砖块 —— 一个完整可玩的小游戏。

演示 gamekit 的核心能力：
- 场景管理（主菜单 / 游戏场景 切换）
- UI 按钮（开始、退出、再来一局、回菜单）
- 碰撞回调（球撞挡板 / 球撞砖块）
- 粒子爆炸特效
- 鼠标控制、计分、生命、胜利/失败判断

运行：python examples/03_breakout.py
"""

import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamekit import Game, Scene, Key

W, H = 720, 620
BRICK_COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6"]


class MenuScene(Scene):
    """主菜单。"""

    def on_enter(self, game):
        game.bg_color = "#101018"
        game.text("打 砖 块", x=W // 2, y=170, size=60, bold=True)
        game.text("移动鼠标控制挡板，接住小球，击碎所有砖块",
                  x=W // 2, y=240, size=16, color="#888888")
        game.text("每击碎一块 +10 分，漏掉球扣 1 条命",
                  x=W // 2, y=270, size=14, color="#666666")
        game.button("开 始 游 戏", x=W // 2, y=360, width=200, height=56,
                    on_click=lambda b: self.game.switch_scene(GameScene()))
        game.button("退 出", x=W // 2, y=440, width=120, height=40,
                    on_click=lambda b: self.game.stop())

    def on_exit(self):
        self.clear()


class GameScene(Scene):
    """游戏主体。"""

    def __init__(self):
        super().__init__("game")
        self.score = 0
        self.lives = 3
        self.state = "play"     # play / win / lose
        self.bricks_left = 0

    # ---- 进入场景 ----
    def on_enter(self, game):
        self.game = game
        game.bg_color = "#101018"

        # 挡板
        self.paddle = game.sprite(color="white", x=W // 2, y=H - 40,
                                  width=110, height=18)
        # 球
        self.ball = game.sprite(color="#ffcc00", x=W // 2, y=H - 80,
                                width=16, height=16, shape="circle")
        # 砖块阵
        self._make_bricks()
        # UI
        self.score_text = game.text("得分 0", x=70, y=26, size=18)
        self.lives_text = game.text("生命 3", x=W - 70, y=26, size=18)
        self.hint_text = game.text("移动鼠标控制挡板 · ESC 回菜单",
                                   x=W // 2, y=H - 14, size=13, color="#555555")

        # 发射球
        self.ball.vx = random.choice([-1, 1]) * 240
        self.ball.vy = -260

        # 注册碰撞回调（场景切换时会自动清理，所以每次进入都要重新注册）
        game.on_collide(self.ball, self.paddle)(self._on_ball_paddle)
        game.on_collide(self.ball, "brick")(self._on_ball_brick)

    def _make_bricks(self):
        rows, cols, gap = 6, 9, 6
        bw, bh = 64, 24
        start_x = (W - cols * (bw + gap)) // 2 + bw // 2
        for r in range(rows):
            for c in range(cols):
                self.game.sprite(color=BRICK_COLORS[r],
                                 x=start_x + c * (bw + gap), y=72 + r * (bh + gap),
                                 width=bw, height=bh, tag="brick")
                self.bricks_left += 1

    # ---- 每帧逻辑 ----
    def on_update(self, dt):
        if self.state != "play":
            return
        # 挡板跟随鼠标
        self.paddle.x = max(60, min(W - 60, self.game.mouse_x))

        # 球：上下墙反弹
        if self.ball.y - 8 < 0:
            self.ball.y = 8
            self.ball.vy = abs(self.ball.vy)

        # 球落底：损失一条命
        if self.ball.y > H + 20:
            self.lives -= 1
            self.lives_text.set("生命 %d" % self.lives)
            if self.lives <= 0:
                self._end(won=False)
            else:
                self._reset_ball()

    def _reset_ball(self):
        self.ball.move_to(self.paddle.x, H - 80)
        self.ball.vx = random.choice([-1, 1]) * 240
        self.ball.vy = -260

    def _end(self, won):
        self.state = "win" if won else "lose"
        self.ball.visible = False
        self.paddle.visible = False
        title = "胜 利 ！" if won else "游 戏 结 束"
        color = "#6bff9c" if won else "#ff6b6b"
        self.game.text(title, x=W // 2, y=230, size=56, bold=True, color=color)
        self.game.text("最终得分 %d" % self.score, x=W // 2, y=300, size=26)
        self.game.button("再 来 一 局", x=W // 2 - 120, y=380, width=180, height=52,
                         on_click=lambda b: self.game.switch_scene(GameScene()))
        self.game.button("回 主 菜 单", x=W // 2 + 120, y=380, width=180, height=52,
                         on_click=lambda b: self.game.switch_scene(MenuScene()))

    def on_exit(self):
        self.clear()

    # ---- 碰撞回调（进入场景时注册）----
    def _on_ball_paddle(self, ball, paddle):
        # 只在球向下运动时反弹，避免粘在挡板上
        if ball.vy > 0:
            ball.vy = -abs(ball.vy)
            # 击打位置偏移影响水平方向
            ball.vx += (ball.x - paddle.x) * 2.2
            ball.vx = max(-420, min(420, ball.vx))

    def _on_ball_brick(self, ball, brick):
        self.score += 10
        self.bricks_left -= 1
        self.score_text.set("得分 %d" % self.score)
        # 粒子爆炸（颜色取砖块颜色）
        self.game.burst(ball.x, ball.y, count=16,
                        colors=(brick.color, "#ffffff", "#ffd700"), speed=(40, 180))
        brick.remove()
        # 反弹：根据重叠方向
        ball.bounce_off(brick, restitution=1.0)
        if self.bricks_left <= 0:
            self._end(won=True)


def main():
    game = Game(title="打砖块 · gamekit", width=W, height=H, fps=60)
    game.add_scene(MenuScene())
    game.switch_scene(MenuScene())

    @game.on_key(Key.ESCAPE)
    def back_to_menu():
        if game.current_scene and game.current_scene.name == "game":
            game.switch_scene(MenuScene())

    if "--selftest" in sys.argv:
        game.after(2.0, game.stop)

    game.run()


if __name__ == "__main__":
    main()
