"""示例 05：太空射击 —— gamekit 综合实战。

用到了：精灵、键盘持续输入、标签碰撞、粒子爆炸、文字计分、
场景切换、UI 按钮、定时生成敌人。

操作：← → / A D 移动，空格射击（可按住连发），别被敌机撞到。
运行：python examples/05_space_shooter.py
"""

import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamekit import Game, Scene, Key

W, H = 640, 700


class GameScene(Scene):
    """游戏主体。"""

    def __init__(self):
        super().__init__("game")
        self.score = 0
        self.lives = 3
        self.state = "play"       # play / over
        self.shoot_cd = 0.0       # 射击冷却
        self.spawn_timer = 0.0    # 敌人生成计时
        self.spawn_interval = 1.2

    def on_enter(self, game):
        self.game = game
        game.bg_color = "#0a0e18"

        # 玩家飞船
        self.player = game.sprite(color="#4ac0f0", x=W // 2, y=H - 60,
                                  width=50, height=40)
        self.player.keep_on_screen = True

        # 计分 / 生命
        self.score_text = game.text("得分 0", x=90, y=26, size=20, bold=True)
        self.lives_text = game.text("生命 3", x=W - 90, y=26, size=20, bold=True)

        # 注册碰撞回调（场景切换会自动清理，每次进入重新注册）
        game.on_collide("bullet", "enemy")(self._on_bullet_enemy)
        game.on_collide("enemy", self.player)(self._on_enemy_player)

    def on_update(self, dt):
        if self.state != "play":
            return

        # 移动（键盘 ←→ / A D，也支持鼠标）
        if self.game.is_key_down(Key.LEFT) or self.game.is_key_down("a"):
            self.player.vx = -320
        elif self.game.is_key_down(Key.RIGHT) or self.game.is_key_down("d"):
            self.player.vx = 320
        else:
            self.player.vx = 0

        # 射击（按住空格 = 自动连发）
        if self.game.is_key_down(Key.SPACE):
            self.shoot()
        self.shoot_cd -= dt

        # 定时生成敌人
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = self.spawn_interval
            self.spawn_enemy()

        # 清理飞出屏幕的敌人
        for e in self.game.find("enemy"):
            if e.y > H + 30:
                e.remove()

    # ---- 游戏逻辑 ----
    def spawn_enemy(self):
        e = self.game.sprite(color=random.choice(["#ff6b6b", "#ff9f43", "#c86bff"]),
                             x=random.randint(40, W - 40), y=-20,
                             width=36, height=30, tag="enemy")
        e.vy = random.randint(120, 220)

    def shoot(self):
        if self.shoot_cd > 0 or self.state != "play":
            return
        self.shoot_cd = 0.28
        self.game.sprite(color="#ffd700", x=self.player.x, y=self.player.y - 26,
                         width=6, height=14, tag="bullet").vy = -520

    # ---- 碰撞回调 ----
    def _on_bullet_enemy(self, bullet, enemy):
        self.score += 10
        self.score_text.set("得分 %d" % self.score)
        self.game.burst(enemy.x, enemy.y, count=16,
                        colors=("orange", "yellow", "white"))
        bullet.remove()
        enemy.remove()

    def _on_enemy_player(self, enemy, player):
        if self.state != "play":
            return
        self.lives -= 1
        self.lives_text.set("生命 %d" % self.lives)
        self.game.burst(player.x, player.y, count=20, colors=("cyan", "white"))
        enemy.remove()
        if self.lives <= 0:
            self._game_over()

    def _game_over(self):
        self.state = "over"
        for e in self.game.find("enemy"):
            e.remove()
        self.game.text("游 戏 结 束", x=W // 2, y=280, size=48, bold=True, color="#ff6b6b")
        self.game.text("得分 %d" % self.score, x=W // 2, y=340, size=26)
        self.game.button("再玩一次", x=W // 2, y=410, width=160, height=48,
                         on_click=lambda b: self.game.switch_scene(GameScene()))
        self.game.button("回主菜单", x=W // 2, y=480, width=160, height=48,
                         on_click=lambda b: self.game.switch_scene(MenuScene()))

    def on_exit(self):
        self.clear()


class MenuScene(Scene):
    """主菜单。"""

    def on_enter(self, game):
        game.bg_color = "#0a0e18"
        game.text("太 空 射 击", x=W // 2, y=240, size=52, bold=True, color="#4ac0f0")
        game.text("← → 移动 · 空格射击 · 别被撞到！",
                  x=W // 2, y=310, size=16, color="#8899aa")
        game.button("开 始 游 戏", x=W // 2, y=390, width=200, height=54,
                    on_click=lambda b: self.game.switch_scene(GameScene()))
        game.button("退 出", x=W // 2, y=470, width=140, height=42,
                    on_click=lambda b: self.game.stop())

    def on_exit(self):
        self.clear()


def main():
    game = Game(title="太空射击 · gamekit", width=W, height=H, fps=60)

    @game.on_key(Key.ESC)
    def quit_game():
        game.stop()

    game.switch_scene(MenuScene())

    # 自动化验证：进入游戏场景 → 开火 → 放一个敌人正对枪口 → 检查得分
    if "--selftest" in sys.argv:
        def auto_test():
            game.switch_scene(GameScene())
            scene = game.current_scene
            scene.shoot()
            game.sprite(color="red", x=scene.player.x, y=scene.player.y - 120,
                        width=36, height=30, tag="enemy").vy = 0

        def finish():
            s = game.current_scene
            score = getattr(s, "score", 0)
            print("太空射击 selftest: score = %d" % score)
            assert score > 0, "子弹应击中敌人得分，碰撞逻辑异常"
            game.stop()

        game.after(0.5, auto_test)
        game.after(2.5, finish)

    game.run()


if __name__ == "__main__":
    main()
