# learn_pygame/05_camera_tilemap.py
# Camera + Tilemap 演示：大地图关卡，相机跟随玩家。
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gamekit import Game

W, H = 640, 400
TILE = 32

MAP = [
    "####################",
    "#..................#",
    "#..................#",
    "#....####....####..#",
    "#..................#",
    "#..S...............#",
    "#..................#",
    "#......#####.......#",
    "#..................#",
    "#..................#",
    "####################",
]

g = Game("camera + tilemap", W, H, fps=60, backend="gdi")
g.tilemap(MAP, tile_size=TILE, tile_defs={"#": "#3a7", "S": "#f40"})
player = g.sprite(color="#ff0", x=3*TILE, y=5*TILE, width=TILE, height=TILE)

@g.on_key_hold("left")
def _l(dt): player.x -= 200*dt

@g.on_key_hold("right")
def _r(dt): player.x += 200*dt

@g.on_key_hold("up")
def _u(dt): player.y -= 200*dt

@g.on_key_hold("down")
def _d(dt): player.y += 200*dt

@g.on_update
def follow(dt):
    map_w = len(MAP[0]) * TILE
    map_h = len(MAP) * TILE
    g.camera_x = max(0, min(player.x + TILE/2 - W/2, map_w - W))
    g.camera_y = max(0, min(player.y + TILE/2 - H/2, map_h - H))

if "--selftest" in sys.argv:
    import threading
    player.x = 5*TILE   # 让相机平移一下
    threading.Timer(1.5, g.stop).start()

g.run()
print("OK")
