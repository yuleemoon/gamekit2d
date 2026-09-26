# learn_pygame/06_platformer.py
# 横版平台跳跃 demo：tilemap 关卡 + 重力 + 跳跃 + 碰撞 + 相机跟随。
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gamekit import Game, rect_collide

W, H = 640, 400
TILE = 32

# 关卡：# = 砖, . = 空气, S = 玩家出生, C = 金币
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

g = Game("platformer", W, H, fps=60, backend="gdi")

# 铺砖（tilemap 自动 static）
tiles = g.tilemap(MAP, tile_size=TILE,
                  tile_defs={"#": "#4a6", "S": "#f40"})

# 玩家
player = g.sprite(color="#ff0", x=3*TILE+TILE/2, y=5*TILE+TILE/2, width=24, height=24)
player.vx = 0
player.vy = 0
player.on_ground = False

GRAVITY = 1500       # 像素/秒²
JUMP_V = -520
SPEED = 260

keys = set()

@g.on_key_hold("left")
def _l(dt):
    player.vx = -SPEED

@g.on_key_hold("right")
def _r(dt):
    player.vx = SPEED

@g.on_key("up")
def _jump():
    if player.on_ground:
        player.vy = JUMP_V

# 记录哪些键按着，松开对应方向时才减速
_held = set()

@g.on_key_down("left")
def _dl():
    _held.add("L")

@g.on_key_down("right")
def _dr():
    _held.add("R")

@g.on_key_up("left")
def _ul():
    _held.discard("L")

@g.on_key_up("right")
def _ur():
    _held.discard("R")

def move_and_collide(dx, dy):
    """分轴移动，撞砖就回退（Sprite x/y 是中心点）。
    只处理第一个碰撞，避免墙角多砖重叠时位置互相打架。"""
    # 水平：只在真正从侧面撞进来时回退（站在砖正下方/正上方不推）
    player.x += dx
    pl = player.x - player.width/2
    pr = player.x + player.width/2
    for t in tiles:
        if t._removed or not t.visible:
            continue
        tl = t.x - t.width/2
        tr = t.x + t.width/2
        if not (pl < tr and pr > tl):
            continue   # 水平方向根本不重叠
        if not (player.y - player.height/2 < t.y + t.height/2
                and player.y + player.height/2 > t.y - t.height/2):
            continue
        # 从右边撞进来（玩家左边缘穿过砖左边缘）
        if dx > 0 and pr > tl and pl < tl:
            player.x = tl - player.width/2
        # 从左边撞进来（玩家右边缘穿过砖右边缘）
        elif dx < 0 and pl < tr and pr > tr:
            player.x = tr + player.width/2
        break
    # 垂直
    player.y += dy
    player.on_ground = False
    for t in tiles:
        if t._removed or not t.visible:
            continue
        if rect_collide(player, t):
            if dy > 0:
                player.y = t.y - t.height/2 - player.height/2
                player.vy = 0
                player.on_ground = True
            elif dy < 0:
                player.y = t.y + t.height/2 + player.height/2
                player.vy = 0
            break

@g.on_update
def update(dt):
    # 水平速度：按方向键直接给速度，松开按当前方向有摩擦
    if "L" in _held:
        player.vx = -SPEED
    elif "R" in _held:
        player.vx = SPEED
    elif player.on_ground:
        player.vx *= 0.6   # 地面摩擦，松手快速停下
    else:
        player.vx *= 0.98  # 空中微弱阻力

    player.vy += GRAVITY * dt
    if player.vy > 900:
        player.vy = 900
    move_and_collide(player.vx * dt, player.vy * dt)
    # 相机跟随，居中
    map_w = len(MAP[0]) * TILE
    map_h = len(MAP) * TILE
    g.camera_x = max(0, min(player.x - W/2, map_w - W))
    g.camera_y = max(0, min(player.y - H/2, map_h - H))

if "--selftest" in sys.argv:
    import threading
    player.x = 8*TILE + TILE/2
    threading.Timer(2.0, g.stop).start()

g.run()
print("OK")
