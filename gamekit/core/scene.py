"""场景：把一个游戏拆分成多个独立场景（如菜单、关卡、结束画面）。"""


class Scene:
    """一个游戏场景。

    场景持有自己的精灵 / 文本 / UI / 粒子列表；调用 ``game.switch_scene``
    切换后，游戏只渲染和更新当前场景的内容。

    用法：:

        class MenuScene(Scene):
            def on_enter(self, game):
                game.text("点我开始", x=400, y=300, size=32)

            def on_update(self, dt):
                ...
    """

    def __init__(self, name="Scene"):
        self.name = name
        self.game = None
        self.sprites = []
        self.shapes = []
        self.texts = []
        self.ui_elements = []
        self.particles = []

    # ---- 生命周期钩子（子类重写）----
    def on_enter(self, game):
        """进入本场景时调用（在此创建精灵、注册事件）。"""

    def on_exit(self):
        """离开本场景时调用。"""

    def on_update(self, dt):
        """本场景每帧更新时调用（dt 为秒）。"""

    # ---- 便捷创建：把对象创建到本场景 ----
    def sprite(self, *args, **kwargs):
        s = self.game.sprite(*args, **kwargs)
        if self.game._sprites is not self.sprites and s not in self.sprites:
            self.sprites.append(s)
        return s

    def line(self, *args, **kwargs):
        sh = self.game.line(*args, **kwargs)
        if self.game._shapes is not self.shapes and sh not in self.shapes:
            self.shapes.append(sh)
        return sh

    def polygon(self, *args, **kwargs):
        sh = self.game.polygon(*args, **kwargs)
        if self.game._shapes is not self.shapes and sh not in self.shapes:
            self.shapes.append(sh)
        return sh

    def ellipse(self, *args, **kwargs):
        sh = self.game.ellipse(*args, **kwargs)
        if self.game._shapes is not self.shapes and sh not in self.shapes:
            self.shapes.append(sh)
        return sh

    def arc(self, *args, **kwargs):
        sh = self.game.arc(*args, **kwargs)
        if self.game._shapes is not self.shapes and sh not in self.shapes:
            self.shapes.append(sh)
        return sh

    def text(self, *args, **kwargs):
        t = self.game.text(*args, **kwargs)
        if self.game._texts is not self.texts and t not in self.texts:
            self.texts.append(t)
        return t

    def button(self, *args, **kwargs):
        b = self.game.button(*args, **kwargs)
        if self.game._ui_elements is not self.ui_elements and b not in self.ui_elements:
            self.ui_elements.append(b)
        return b

    def particles(self, *args, **kwargs):
        p = self.game.particles(*args, **kwargs)
        if self.game._particles is not self.particles and p not in self.particles:
            self.particles.append(p)
        return p

    def clear(self):
        """清空本场景所有对象。"""
        self.sprites.clear()
        self.shapes.clear()
        self.texts.clear()
        self.ui_elements.clear()
        self.particles.clear()

    def __repr__(self):
        return "Scene(%s)" % self.name
