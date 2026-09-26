"""UI 控件：按钮、进度条。

这些控件由 Game 统一管理：按钮自动响应点击（悬停高亮），
进度条按值自动绘制填充比例。
"""

from ..utils.color import to_color, mix


class Button:
    """一个带文字和悬停高亮效果的按钮。

    :param text: 按钮文字
    :param x, y: 中心坐标
    :param width, height: 按钮尺寸
    :param color / hover_color: 常态 / 悬停颜色
    :param text_color: 文字颜色
    :param font_size: 字号
    :param on_click: 点击回调 ``fn(button)``
    """

    def __init__(self, game, text="Button", x=0, y=0, width=140, height=44,
                 color="#3a6ea5", hover_color="#4a88c9", text_color="white",
                 font_size=18, on_click=None):
        self.game = game
        self.text = str(text)
        self.x = float(x)
        self.y = float(y)
        self.width = float(width)
        self.height = float(height)
        self.color = to_color(color)
        self.hover_color = to_color(hover_color)
        self.text_color = to_color(text_color)
        self.font_size = int(font_size)
        self.on_click = on_click
        self.visible = True
        self.enabled = True
        self.tag = None
        self._removed = False

    @property
    def left(self):
        return self.x - self.width / 2

    @property
    def right(self):
        return self.x + self.width / 2

    @property
    def top(self):
        return self.y - self.height / 2

    @property
    def bottom(self):
        return self.y + self.height / 2

    def contains(self, x, y):
        return self.left <= x <= self.right and self.top <= y <= self.bottom

    def remove(self):
        if not self._removed:
            self._removed = True
            self.game._remove_ui(self)
        return self

    def _handle_click(self, x, y):
        if self.visible and self.enabled and self.contains(x, y):
            if self.on_click:
                self.on_click(self)

    def _draw(self, r):
        if not self.visible:
            return
        hovering = self.contains(self.game.mouse_x, self.game.mouse_y)
        fill = self.hover_color if (hovering and self.enabled) else self.color
        r.draw_rect(self.left, self.top, self.right, self.bottom, fill)
        # 顶部高光，让按钮更有立体感
        r.draw_rect(self.left, self.top, self.right, self.top + 3,
                    mix(fill, "white", 0.3))
        weight = "bold" if self.enabled else "normal"
        r.draw_text(self.x, self.y, self.text, self.text_color,
                    "Microsoft YaHei", self.font_size, weight, "roman", "center")


class ProgressBar:
    """一个水平进度条。

    :param x, y: 中心坐标
    :param width, height: 尺寸
    :param value / max_value: 当前值 / 最大值
    :param color: 填充颜色
    :param bg: 背景颜色
    """

    def __init__(self, game, x=0, y=0, width=240, height=20,
                 value=0.0, max_value=100.0, color="#4caf50", bg="#333333"):
        self.game = game
        self.x = float(x)
        self.y = float(y)
        self.width = float(width)
        self.height = float(height)
        self.value = float(value)
        self.max_value = float(max_value) if max_value else 1.0
        self.color = to_color(color)
        self.bg = to_color(bg)
        self.visible = True
        self.tag = None
        self._removed = False

    @property
    def ratio(self):
        """当前比例 0.0 ~ 1.0。"""
        if self.max_value <= 0:
            return 0.0
        return max(0.0, min(1.0, self.value / self.max_value))

    def set_value(self, value):
        self.value = float(value)
        return self

    def remove(self):
        if not self._removed:
            self._removed = True
            self.game._remove_ui(self)
        return self

    def _draw(self, r):
        if not self.visible:
            return
        left, top = self.x - self.width / 2, self.y - self.height / 2
        # 背景
        r.draw_rect(left, top, left + self.width, top + self.height, self.bg)
        # 填充
        w = self.width * self.ratio
        if w > 1:
            r.draw_rect(left + 2, top + 2,
                        left + w - 2, top + self.height - 2, self.color)
