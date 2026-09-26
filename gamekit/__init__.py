"""gamekit —— 一个零第三方依赖的极简 2D 游戏库。

只使用 Python 标准库（自研 GDI 渲染 + tkinter 保底 + winsound），API 简单到极致：
创建一个 ``Game``、创建几个 ``Sprite``、注册几个回调、``run()`` 一行开跑。

快速上手：:

    from gamekit import Game, Key

    game = Game(title="我的第一个游戏", width=800, height=600, fps=60)

    player = game.sprite(color="red", x=400, y=500, width=60, height=40)

    @game.on_key(Key.LEFT)
    def left():
        player.vx = -300

    @game.on_key(Key.RIGHT)
    def right():
        player.vx = 300

    @game.on_key(Key.SPACE)
    def stop():
        player.vx = 0

    game.run()
"""

from .core.game import Game
from .core.scene import Scene
from .core.keys import Key, normalize
from .sprites.sprite import Sprite
from .sprites.group import Group
from .sprites.animation import Animation
from .physics.collision import (rect_collide, circle_collide, point_in_rect,
                                point_in_circle, distance, collides,
                                pixel_collide)
from .audio.sound import Sound
from .ui.text import Text
from .ui.widgets import Button, ProgressBar
from .fx.particles import ParticleSystem
from .fx.draw import Line, Polygon, Ellipse, Arc
from .input.gamepad import Gamepad
from .input.camera import Camera
from .utils.color import (Color, to_color, mix, random_color,
                          RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, PINK,
                          CYAN, LIME, MAGENTA, BROWN, WHITE, BLACK, GRAY,
                          LIGHT_GRAY, DARK_GRAY, NAVY)
from .utils.vector import Vec2

__version__ = "1.0.2"
__all__ = [
    "Game", "Scene", "Key", "normalize",
    "Sprite", "Group", "Animation",
    "rect_collide", "circle_collide", "point_in_rect", "point_in_circle",
    "distance", "collides", "pixel_collide",
    "Sound",
    "Text", "Button", "ProgressBar",
    "ParticleSystem",
    "Line", "Polygon", "Ellipse", "Arc",
    "Gamepad", "Camera",
    "Color", "to_color", "mix", "random_color",
    "RED", "GREEN", "BLUE", "YELLOW", "ORANGE", "PURPLE", "PINK",
    "CYAN", "LIME", "MAGENTA", "BROWN", "WHITE", "BLACK", "GRAY",
    "LIGHT_GRAY", "DARK_GRAY", "NAVY",
    "Vec2",
]
