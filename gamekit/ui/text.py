"""文本对象：在画布上显示文字。"""

from ..utils.color import to_color


class Text:
    """显示在屏幕上的文本。

    :param content: 文本内容
    :param x, y: 坐标（默认以中心为锚点，可用 ``anchor`` 调整）
    :param size: 字号
    :param color: 颜色
    :param font: 字体族名称（默认 "Microsoft YaHei"，中文友好）
    :param anchor: tkinter 锚点，如 "center" / "nw" / "n"
    :param bold: 是否加粗
    """

    def __init__(self, game, content="", x=0, y=0, size=20, color="white",
                 font=None, anchor="center", bold=False, italic=False):
        self.game = game
        self.content = str(content)
        self.x = float(x)
        self.y = float(y)
        self.size = int(size)
        self.color = to_color(color)
        self.font_family = font or "Microsoft YaHei"
        self.anchor = anchor
        self.bold = bool(bold)
        self.italic = bool(italic)
        self.visible = True
        self._removed = False
        self.tag = None

    def set(self, content):
        """更新文本内容（常用写法：``score_text.set("得分: %d" % score)``）。"""
        self.content = str(content)
        return self

    def move_to(self, x, y):
        self.x = float(x)
        self.y = float(y)
        return self

    def remove(self):
        if not self._removed:
            self._removed = True
            self.game._remove_text(self)
        return self

    def _draw(self, r):
        if not self.visible:
            return
        weight = "bold" if self.bold else "normal"
        slant = "italic" if self.italic else "roman"
        r.draw_text(
            self.x, self.y,
            content=self.content,
            color=self.color,
            font=self.font_family,
            size=self.size,
            weight=weight,
            slant=slant,
            anchor=self.anchor,
        )
