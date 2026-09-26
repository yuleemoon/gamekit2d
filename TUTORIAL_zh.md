# gamekit — pygame，减去样板代码

你想做一个 2D 游戏，可每次打开 pygame 文档，都得先花一个小时搭窗口和事件循环，屏幕上一个东西都还没动。

gamekit 是反过来的。一个类、十几个方法、零第三方依赖（只用标准库：Windows 上用自研 GDI 渲染内核、其他平台用 tkinter，音频用 winsound）。pygame 给你的东西它都有——精灵、输入、碰撞、图像、字体、音效、形状、计时、场景——但你写的代码大概只有 pygame 的三分之一。

这份教程从头走到尾：游戏循环、精灵、移动、输入、碰撞、文字、UI、形状、图像、音效、粒子、场景，最后是一整个完整游戏。每一章都有能直接跑的代码。安装：

```
pip install gamekit2d
```

需要 Python 3.9 或更新。别的什么都不用装。

> **渲染后端。** 默认 `Game(backend="auto")`：Windows 上自动用 gamekit 自研的 GDI 内核（原生窗口 + BitBlt 双缓冲，比 tkinter 快一个数量级，纯色精灵上千个依然流畅），其他平台自动回落 tkinter。也可以 `backend="gdi"` / `backend="tk"` 强制指定。游戏代码感知不到后端差别，切换只需改这一个参数。

---

## 第 0 章 — gamekit 覆盖了什么

下面是 pygame 到 gamekit 的完整对照表。用过 pygame 的话，这就是你要的速查表；没用过就扫一眼继续往下——后面每一章都会逐行解释。

| pygame | gamekit | 说明 |
|---|---|---|
| `pygame.display.set_mode` | `Game(width=, height=)` | 可以顺手传 `fps=` |
| `pygame.display.set_caption` | `Game(title=)` | |
| `pygame.event.get()` / `KEYDOWN` | `@game.on_key(Key.X)` | 装饰器，每次按下触发一次 |
| `pygame.key.get_pressed()` | `game.is_key_down(Key.X)` | 在 `on_update` 里做长按检测 |
| `KEYUP` | `@game.on_key_up(Key.X)` | |
| `MOUSEMOTION` / `MOUSEBUTTONDOWN` | `@game.on_mouse_move` / `on_mouse_down` | |
| `MOUSEBUTTONUP` / `mouse.get_pos` | `@game.on_mouse_up` / `game.mouse_x, game.mouse_y` | |
| `pygame.Sprite` + `pygame.sprite.Group` | `game.sprite()` + `tag=` | tag 替代 Group |
| `pygame.sprite.collide_rect` | `sprite.collides_with(other)` | |
| `pygame.sprite.collide_circle` | 同一个调用 | 圆形精灵自动按圆碰撞 |
| `pygame.draw.rect` | `game.sprite(color=..., shape="rect")` | 实心矩形 |
| `pygame.draw.circle` | `game.sprite(color=..., shape="circle")` | 实心圆 |
| `pygame.draw.line` | `game.line(...)` | |
| `pygame.draw.polygon` | `game.polygon(...)` | |
| `pygame.draw.ellipse` | `game.ellipse(...)` | |
| `pygame.draw.arc` | `game.arc(...)` | |
| `pygame.draw.lines` | `game.polygon(..., outline=...)` | 开放图形变成描边 |
| `pygame.image.load` | `game.sprite("file.png")` | PNG / GIF / BMP / PPM，不支持 JPG |
| `pygame.transform.scale` | `sprite.set_scale(1.5)` | |
| `pygame.transform.rotate` | `sprite.set_angle(45)` | 角度制 |
| `pygame.transform.flip` | `sprite.flip(horizontal=True, vertical=False)` | |
| `pygame.image.save` | `sprite.save_image("out.ppm")` | PPM / GIF / BMP |
| `pygame.font.Font.render` | `game.text(...)` + `.set(...)` | 更新文字用 set，别重建 |
| `pygame.mixer.Sound.play` | `game.sound("hit.wav").play()` | 仅 WAV，仅 Windows |
| `pygame.mixer.music` | `game.music("bgm.wav")` | 默认循环 |
| `pygame.time.Clock.tick` | `fps=60` 传给 `Game` | 已经帮你处理 |
| `pygame.time.get_ticks` | `game.time` | 单位是秒，不是毫秒 |
| `pygame.mask` | `pixel_collide(a, b)` | 像素级精确碰撞，不是完整 mask API |
| `pygame.math.Vector2` | `Vec2` | |
| `pygame.Rect` | `sprite.left/right/top/bottom` | 几何信息直接挂在精灵上 |
| `pygame.Color` | `Color`、具名常量 | |
| `pygame.QUIT` | 自动处理 | 关窗口即停游戏 |
| `pygame.joystick` | — | 标准库不支持手柄 |
| `pygame.camera` | — | 标准库不支持摄像头 |
| `pygame.Surface` + `blit` | 精灵，或 `on_draw` 钩子 | 你不用自己管 Surface |

有两点先说清楚，能帮你省时间：

1. **音频方面 gamekit 以 Windows 为主。** tkinter 哪都能跑，但音频（winsound）只在 Windows 上生效。Linux 或 macOS 上调用 `play()` 会打印一条提示，游戏继续跑。这是零依赖的代价。
2. **没有手柄、没有摄像头。** 标准库里这两样都没有。如果你的游戏非要手柄，请继续用 pygame。对照表里其他所有功能，往下看。

---

## 第 1 章 — 你的第一个窗口

创建 `hello.py`：

```python
from gamekit import Game

game = Game(title="Hello", width=640, height=480, fps=60)
game.run()
```

运行 `python hello.py`。一个深色窗口打开并停留。这已经是游戏了——循环在跑，每秒重绘 60 次背景。

`Game` 对象就是整个库。你通过它创建精灵、注册回调、最后用一个 `run()` 启动一切。

---

## 第 2 章 — 游戏循环

每个游戏都是一个循环。每一轮做三件事：

```
   ┌────────────────┐
   │  1. 读取输入     │──┐
   └────────────────┘  │
            │           │
            ▼           │
   ┌────────────────┐   │
   │  2. 更新世界     │   │
   └────────────────┘   │
            │           │
            ▼           │
   ┌────────────────┐   │
   │  3. 绘制一帧     │   │
   └────────────────┘   │
            │           │
            └───────────┘
```

- 读玩家按了什么键。
- 移动物体、检查碰撞、更新分数。
- 绘制所有东西。

gamekit 按你设的 `fps` 替你跑这个循环。你要写的只有"更新世界"这部分，而且一开始连这个都可以不写。

三个你会经常用的值：

- `game.time` — 游戏启动以来的秒数（类似 `pygame.time.get_ticks`，但单位是秒）。
- `game.dt` — 上一帧花了多少秒。每个更新回调都会把它传给你。
- `fps` — 循环每秒钟跑多少次。

让游戏在不同机器上都表现正常的那条规则：

**永远按"像素/秒"思考，不要按"像素/帧"。**

别写"每帧移动 10 像素"。要写"每秒移动 300 像素"然后乘以 `dt`。这样 60 帧和 30 帧手感完全一致。gamekit 内置的速度就是按这个规则做的，每个示例也都遵循它。

---

## 第 3 章 — 精灵

精灵就是你在屏幕上看到的任何东西。玩家、敌人、子弹、金币——全是精灵。

```python
from gamekit import Game

game = Game(title="Sprites", width=640, height=480)

# 一个红色方块，中心在 (320, 240)
box = game.sprite(color="red", x=320, y=240, width=80, height=80)

# 一个金色圆形
ball = game.sprite(color="gold", x=100, y=100, width=40, height=40, shape="circle")

game.run()
```

坐标和 pygame 里的直觉一致：(0, 0) 在左上角，x 向右增大，y 向下增大。`x` 和 `y` 是精灵的中心。

常用属性：

```python
player = game.sprite(color="skyblue", x=100, y=100, width=60, height=60,
                     shape="rect", tag="player", layer=0)

player.x, player.y          # 位置（中心）
player.vx, player.vy        # 速度，像素/秒
player.width, player.height # 尺寸
player.visible              # True/False
player.layer                # 绘制顺序，越大越靠前
player.tag                  # 标签，用来批量匹配
player.solid                # 是否参与碰撞
```

有两种形状：`"rect"`（默认）和 `"circle"`。圆形精灵也按圆碰撞，而不是按圆外面的方框。图像精灵的 `shape` 会被忽略——图像自己决定尺寸。

`tag` 就是你的分组。在 pygame 里你要建一个 `Group` 来装子弹然后遍历它。这里你给每颗子弹 `tag="bullet"`，然后一次性匹配全部：

```python
enemies = game.find("enemy")   # 所有带这个标签的精灵
```

---

## 第 4 章 — 移动

设一个速度，精灵自己动。不需要手动写 `x += speed`。

```python
game = Game(width=640, height=480)

ball = game.sprite(color="gold", x=320, y=240, width=30, height=30, shape="circle")
ball.vx = 200     # 每秒向右 200 像素
ball.vy = 150     # 每秒向下 150 像素
ball.bounce = 1.0 # 撞到屏幕边缘反弹，1.0 = 完全弹性

game.run()
```

`bounce` 取值 0 到 1。`0.5` 表示球每次反弹损失一半速度。设为 `0`（默认值）球就会飞出屏幕再也不回来。

### 物理开关

```python
game.gravity = 500          # 像素/秒²，只影响 gravity_scale > 0 的精灵

ball = game.sprite(color="cyan", x=320, y=100, width=20, height=20, shape="circle")
ball.gravity_scale = 1.0    # 0 = 忽略重力，2.0 = 下落快一倍
ball.bounce = 0.8           # 撞到地面反弹
ball.friction = 0.5         # 速度随时间衰减
ball.keep_on_screen = True  # 停在边缘而不是反弹
```

`bounce` 和 `keep_on_screen` 二选一，别两个都用——一个是反弹，一个是停住。

### 手动控制

速度是快捷路径。当你需要真正的控制——曲线、跟随鼠标、正弦波——就在 `on_update` 里自己移动精灵：

```python
@game.on_update
def tick(dt):
    player.x += 300 * dt              # 匀速向右

    player.x = game.mouse_x           # 跟随鼠标
    player.y = game.mouse_y

    import math
    player.x = 320 + math.cos(game.time * 2) * 150   # 绕圈
    player.y = 240 + math.sin(game.time * 2) * 150
```

`move(dx, dy)` 做相对位移，`move_to(x, y)` 跳到某个点，`look_at(other)` 让精灵对准另一个精灵或 `(x, y)` 元组。

---

## 第 5 章 — 输入

### 按键：触发一次

`@game.on_key(Key.X)` 在按键按下时执行一次回调。

```python
from gamekit import Game, Key

@game.on_key(Key.SPACE)
def jump():
    player.vy = -400

@game.on_key(Key.ESC)
def quit_game():
    game.stop()

@game.on_key("a")       # 字母可以直接写字符串
def move_left():
    player.vx = -300
```

常用按键常量：`Key.SPACE`、`Key.UP/DOWN/LEFT/RIGHT`、`Key.ENTER`、`Key.ESC`、`Key.TAB`、`Key.SHIFT/CTRL/ALT`、`Key.F1`–`Key.F12`，另外 `"a"`–`"z"` 和 `"0"`–`"9"` 直接写字符串就行。

### 按键：长按（你最常用的那个）

`@game.on_key_hold(Key.X)` 在按住期间每帧触发，回调会收到 `dt`。这才是做移动的正确工具：

```python
@game.on_key_hold(Key.LEFT)
def left():
    player.vx = -300

@game.on_key_hold(Key.RIGHT)
def right():
    player.vx = 300

@game.on_key_up(Key.LEFT)     # 松开时触发
def stop_left():
    player.vx = 0
```

另一种写法，有些人觉得更干净，是在 `on_update` 里查按住状态：

```python
@game.on_update
def tick(dt):
    if game.is_key_down(Key.LEFT):
        player.vx = -300
    elif game.is_key_down(Key.RIGHT):
        player.vx = 300
    else:
        player.vx = 0
```

### 鼠标

```python
@game.on_mouse_click       # 左键，回调 fn(x, y)
def click(x, y):
    print("clicked", x, y)

@game.on_mouse_move        # fn(x, y)
@game.on_mouse_down        # 任意键，fn(x, y, button)
@game.on_mouse_up          # 任意松开，fn(x, y, button)
@game.on_mouse_wheel       # fn(delta, x, y)
```

当前位置随时可读：`game.mouse_x`、`game.mouse_y`。让挡板跟随鼠标只要三行：

```python
@game.on_update
def tick(dt):
    paddle.x = game.mouse_x
```

---

## 第 6 章 — 碰撞

碰撞检测本质上就是问"这两个形状有没有重叠？"

- **矩形**：它们的边有没有交叉？
- **圆形**：圆心距离是否小于半径之和？

gamekit 会自动给出正确答案——两个圆形精灵按圆碰撞，其余按矩形。

### 手动检查

```python
if player.collides_with(enemy):
    print("hit")

if player.contains(x, y):      # 某个点是否在精灵内部？
    print("pointer on player")

d = player.distance_to(enemy)  # 圆心距离
```

### 自动检测，带回调

`@game.on_collide(a, b)` 在两个物体**开始接触的那一刻**触发**一次**——不是每帧。这正是"吃到金币"或"子弹击中敌人"想要的。

```python
# 两个指定精灵
@game.on_collide(player, coin)
def collect(p, c):
    c.remove()

# 精灵对标签——匹配所有 tag 为 "coin" 的精灵
@game.on_collide(player, "coin")
def collect(p, c):
    c.remove()

# 标签对标签
@game.on_collide("bullet", "enemy")
def hit(bullet, enemy):
    bullet.remove()
    enemy.remove()
```

最后一个就是怎么不直接碰精灵就接好射击逻辑。`"bullet"` 和 `"enemy"` 都是标签。

### 反弹

做打砖块、乒乓这类游戏时，`bounce_off` 会反转对应轴并把精灵推出重叠区，这样它不会卡在另一个物体里面：

```python
@game.on_collide(ball, brick)
def hit(ball, brick):
    brick.remove()
    ball.bounce_off(brick)   # 根据撞到哪一边翻转 vx 或 vy
```

### 像素级精确碰撞

矩形在边角会说谎——圆形金币碰到方块的角，即使像素没碰到也会算命中。当这个要紧的时候，用 `pixel_collide`（对应 `pygame.mask`）：

```python
from gamekit import pixel_collide

if pixel_collide(player, coin):   # 两个都必须是图像精灵
    coin.remove()
```

它比较重叠区域里的实际像素：两张图必须在同一位置都有不透明像素才算命中。如果某个精灵没有图像，就自动退回矩形检测。

### 一个完整的跳跃落地

```python
game.gravity = 600
player.gravity_scale = 1.0
ground = game.sprite(color="gray", x=320, y=580, width=640, height=40)

@game.on_collide(player, ground)
def land(p, g):
    if p.vy > 0:                 # 只在下落时落地
        p.y = g.top - p.height / 2
        p.vy = 0
```

---

## 第 7 章 — 文字和字体

```python
title = game.text("Score: 0", x=320, y=30, size=28, color="white",
                  bold=True, anchor="center")
```

- `x, y` — 位置。
- `size` — 字号。`color` — 就是颜色。
- `font` — 字体族，默认是一个对中文支持很好的字体。
- `bold=True`、`italic=True` — 两种都能用。
- `anchor` — `"center"`（默认）、`"nw"`（左上）、`"n"`（顶部居中）等。

### 更新文字用 set，别重建

这是最值得养成的一个习惯。`set()` 原地更新：

```python
score = 0
score_text = game.text("Score: 0", x=320, y=30, size=28)

@game.on_collide(player, "coin")
def collect(p, c):
    global score
    score += 10
    c.remove()
    score_text.set("Score: %d" % score)
```

每帧调用 `game.text()` 来"更新"文字会不断创建对象，很慢。一个文字对象，改一次 `.set()` 一次。

---

## 第 8 章 — UI 组件

### 按钮

```python
game.button("Start", x=320, y=300, width=180, height=52,
            on_click=start_game)     # 回调 fn(button)

def start_game(button):
    button.text = "Running"
```

按钮悬停会高亮，松开时触发 `on_click`。就这些。

### 进度条

```python
hp = game.progress_bar(x=320, y=30, width=300, height=20,
                       value=100, max_value=100, color="lime")

hp.set_value(60)      # 自动换算成比例
```

适合做血条、经验条、计时条。

---

## 第 9 章 — 绘制形状（对应 pygame.draw）

精灵是实心矩形和圆。需要画线、多边形、椭圆或圆弧时，用形状函数。它们像精灵一样被管理——可移动、可分图层、可删除——但只负责显示：**形状不参与碰撞**。需要碰撞就做成精灵。

```python
# 从 (x1, y1) 到 (x2, y2) 的线段
game.line(x1=100, y1=400, x2=300, y2=400, color="white", width=3)

# 由点列表构成的多边形
game.polygon([(400, 400), (440, 350), (480, 400)],
             color="violet", outline=None)

# 椭圆（或圆）以 (x, y) 为中心
game.ellipse(x=120, y=250, width=80, height=40, color="skyblue")

# 椭圆弧——start 和 extent 用角度制，0 = 正右方向，顺时针
game.arc(x=560, y=250, width=60, height=60,
         start=0, extent=270, color="lime", width_px=3)
```

每个形状都返回一个对象，带 `x, y, vx, vy, visible, layer, tag` 和 `remove()`。给一条线设速度它就会飘动。给一个多边形设标签，之后就能找到它。

---

## 第 10 章 — 图像和动画

### 加载、缩放、旋转、翻转

```python
player = game.sprite("player.png", x=320, y=240)  # 第一个参数传路径
player.set_scale(1.5)     # 1.5 倍
player.set_angle(45)      # 45 度
player.flip(horizontal=True)   # 水平镜像
player.set_image("other.png")  # 换图
```

支持格式：**PNG、GIF、BMP、PPM**。不支持 JPG——tkinter 读不了。

旋转和非整数缩放会实时重采样像素。加载时处理少数几个精灵没问题；每帧对一张大图做旋转就慢了。这点记在心里。

### 保存图像

```python
player.save_image("out.ppm")    # 对应 pygame.image.save
```

把精灵当前图像写入文件。PPM、GIF、BMP 都行。PNG 不行，因为标准库写不了 PNG。

### 逐帧动画

```python
# 播放金币闪烁的两帧，4 帧/秒，循环
coin = game.sprite("coin1.png", x=320, y=200)
coin.play(["coin1.png", "coin2.png"], fps=4, loop=True)

coin.stop_animation()
```

示例素材由 `examples/make_assets.py` 生成，它只用标准库画 PNG。

---

## 第 11 章 — 音效

```python
# 播放一次音效
hit = game.sound("hit.wav")
hit.play()

# 循环背景音乐
music = game.music("bgm.wav")    # 等价于 game.sound(path, loop=True)

music.stop()
```

API 就这么多。限制是真实的，再强调一遍：

- **只支持 WAV。** 标准库只能解码 wav。
- **仅 Windows。** 音频用的是 `winsound`。其他平台上 `play()` 会打印一条提示然后继续。
- **一次只能播一个声音。** `winsound` 同时只播一个音频。音乐和音效不能重叠。需要多轨音频的话，pygame 更合适。

想快速来点音效，用 Python 的 `wave` 模块生成一小段 WAV 再播。不需要任何素材管线。

---

## 第 12 章 — 粒子

gamekit 自带的加分项。爆炸、火花、彩带——便宜又好用。

```python
# 一次性爆炸
game.burst(x=320, y=240, count=40,
           colors=("orange", "yellow", "red"),   # 随机挑选
           speed=(50, 260),        # 初始速度范围，像素/秒
           life=(0.4, 1.5))        # 存活时长范围，秒

# 一个可以反复触发的粒子系统
stars = game.particles(x=320, y=200, count=30, colors=("white", "cyan"))
stars.burst()              # 发射一批
stars.burst(count=60)      # 或指定数量
```

在碰撞回调里打一个粒子爆发，是让命中手感变好的最快办法：

```python
@game.on_collide("bullet", "enemy")
def hit(bullet, enemy):
    game.burst(enemy.x, enemy.y, count=20, colors=("orange", "yellow"))
    bullet.remove()
    enemy.remove()
```

---

## 第 13 章 — 场景

真正的游戏有菜单、游玩画面和游戏结束画面。这就是 `Scene` 的用途。一个场景拥有自己的精灵、文字、按钮和粒子；切换场景时它们会被整体换掉。

```python
from gamekit import Game, Scene

class MenuScene(Scene):
    def on_enter(self, game):          # 在这里搭场景
        game.text("My Game", x=320, y=200, size=48, bold=True)
        game.button("Start", x=320, y=320, on_click=self.start)

    def start(self, button):
        self.game.switch_scene(GameScene())

    def on_exit(self):                 # 离开场景时清理
        self.clear()

class GameScene(Scene):
    def on_enter(self, game):
        self.player = game.sprite(color="cyan", x=320, y=400, width=50, height=50)

    def on_update(self, dt):
        # 这个场景的逐帧逻辑
        ...

game = Game(width=640, height=480)
game.switch_scene(MenuScene())
game.run()
```

关于场景值得知道的事：

- `on_enter` 创建该场景的一切。`on_exit` 清理它。
- 碰撞回调在每次切换场景时会被清空，所以要在 `on_enter` 里注册需要的那些。按键、鼠标和更新回调是全局的，切换场景后仍然有效。
- `game.switch_scene(Scene)` 先调用旧场景的 `on_exit`，再调用新场景的 `on_enter`。

---

## 第 14 章 — Vec2 和颜色

两个处理实际数学的小帮手。

### Vec2

```python
from gamekit import Vec2

v = Vec2(3, 4)
v.length()          # 5.0
v.normalized()      # 单位向量
v2 = Vec2.from_angle(45, 10)   # 45 度方向，每秒 10 像素
v.rotated(90)       # 旋转向量
v.dot(other)        # 点积
```

适合按角度开火，或者让子弹指向玩家：

```python
direction = (Vec2(enemy.x, enemy.y) - Vec2(player.x, player.y)).normalized()
bullet.vx = direction.x * 300
bullet.vy = direction.y * 300
```

### Color

```python
from gamekit import RED, GOLD, to_color, mix

sprite.color = RED                 # 具名常量（一个 Color 对象）
sprite.color = (255, 100, 0)       # (r, g, b) 元组
sprite.color = "#ff6400"           # 十六进制字符串
sprite.color = mix("red", "blue", 0.5)   # 两者正中间
```

任何接受颜色的 API 都接受这三种形式。`Color(r, g, b)` 需要时给你 `.hex` 和 `.tuple`。

---

## 第 15 章 — 完整游戏：太空射击

上面所有内容，放进一个文件。左右移动，空格射击（按住连发），打敌人得分，别被打中。

```python
import random
from gamekit import Game, Scene, Key

W, H = 640, 700

class GameScene(Scene):
    def __init__(self):
        super().__init__("game")
        self.score = 0
        self.lives = 3
        self.state = "play"        # play / over
        self.shoot_cd = 0.0        # 开火冷却
        self.spawn_timer = 0.0     # 敌人生成计时

    def on_enter(self, game):
        self.game = game
        game.bg_color = "#0a0e18"

        self.player = game.sprite(color="#4ac0f0", x=W // 2, y=H - 60,
                                  width=50, height=40)
        self.player.keep_on_screen = True

        self.score_text = game.text("Score 0", x=90, y=26, size=20, bold=True)
        self.lives_text = game.text("Lives 3", x=W - 90, y=26, size=20, bold=True)

        # 在这里注册碰撞——切换场景时会被清空
        game.on_collide("bullet", "enemy")(self._on_bullet_enemy)
        game.on_collide("enemy", self.player)(self._on_enemy_player)

    def on_update(self, dt):
        if self.state != "play":
            return

        if self.game.is_key_down(Key.LEFT) or self.game.is_key_down("a"):
            self.player.vx = -320
        elif self.game.is_key_down(Key.RIGHT) or self.game.is_key_down("d"):
            self.player.vx = 320
        else:
            self.player.vx = 0

        if self.game.is_key_down(Key.SPACE):   # 按住连发
            self.shoot()
        self.shoot_cd -= dt

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = 1.2
            self.spawn_enemy()

        for e in self.game.find("enemy"):
            if e.y > H + 30:
                e.remove()

    def spawn_enemy(self):
        self.game.sprite(color=random.choice(["#ff6b6b", "#ff9f43", "#c86bff"]),
                         x=random.randint(40, W - 40), y=-20,
                         width=36, height=30, tag="enemy").vy = random.randint(120, 220)

    def shoot(self):
        if self.shoot_cd > 0 or self.state != "play":
            return
        self.shoot_cd = 0.28
        self.game.sprite(color="#ffd700", x=self.player.x, y=self.player.y - 26,
                         width=6, height=14, tag="bullet").vy = -520

    def _on_bullet_enemy(self, bullet, enemy):
        self.score += 10
        self.score_text.set("Score %d" % self.score)
        self.game.burst(enemy.x, enemy.y, count=16,
                        colors=("orange", "yellow", "white"))
        bullet.remove()
        enemy.remove()

    def _on_enemy_player(self, enemy, player):
        if self.state != "play":
            return
        self.lives -= 1
        self.lives_text.set("Lives %d" % self.lives)
        self.game.burst(player.x, player.y, count=20, colors=("cyan", "white"))
        enemy.remove()
        if self.lives <= 0:
            self._game_over()

    def _game_over(self):
        self.state = "over"
        for e in self.game.find("enemy"):
            e.remove()
        self.game.text("GAME OVER", x=W // 2, y=280, size=48, bold=True, color="#ff6b6b")
        self.game.text("Score %d" % self.score, x=W // 2, y=340, size=26)
        self.game.button("Play again", x=W // 2, y=410, width=160, height=48,
                         on_click=lambda b: self.game.switch_scene(GameScene()))
        self.game.button("Menu", x=W // 2, y=480, width=160, height=48,
                         on_click=lambda b: self.game.switch_scene(MenuScene()))

    def on_exit(self):
        self.clear()

class MenuScene(Scene):
    def on_enter(self, game):
        game.bg_color = "#0a0e18"
        game.text("SPACE SHOOTER", x=W // 2, y=240, size=52, bold=True, color="#4ac0f0")
        game.text("Arrows / AD to move, space to shoot. Don't get hit.",
                  x=W // 2, y=310, size=16, color="#8899aa")
        game.button("PLAY", x=W // 2, y=390, width=200, height=54,
                    on_click=lambda b: self.game.switch_scene(GameScene()))
        game.button("QUIT", x=W // 2, y=470, width=140, height=42,
                    on_click=lambda b: self.game.stop())

    def on_exit(self):
        self.clear()

def main():
    game = Game(title="Space Shooter", width=W, height=H, fps=60)

    @game.on_key(Key.ESC)
    def quit_game():
        game.stop()

    game.switch_scene(MenuScene())
    game.run()

if __name__ == "__main__":
    main()
```

保存为 `space_shooter.py` 然后运行。每一行都用到前面章节里的东西：精灵、长按输入、标签碰撞、粒子、文字、场景、按钮。

---

## 第 16 章 — 常见问题与坑

**窗口一开就关闭。**
加一个 ESC 处理器，或者脚本结尾加 `input()` 把窗口挂住。

**文字更新很慢。**
你在循环里调用 `game.text()` 了。创建一次，之后用 `.set()`。

**精灵不动。**
你设了 `vx`/`vy` 吗？还是在 `on_update` 里改 `x`/`y`？两个都没有的话，自然不动。再检查它是不是 `visible`。

**碰撞一直不触发。**
两个精灵都需要 `solid=True`（默认）和 `visible=True`（默认）。另外记住 `on_collide` 是进入接触时触发一次，不是每帧——一直贴在一起的组合不会重复触发，除非它们分开再碰一次。

**文字显示成方块或乱码。**
默认字体支持中文；如果自定义 `font=` 渲染不了某个字形，换回默认字体或一个你确定已安装的字体。

**图片加载失败。**
只支持 PNG、GIF、BMP、PPM，不支持 JPG。检查路径和文件是否存在。

**性能建议。**
几百个实心精灵跑得很流畅；几千个就会掉帧，因为每帧都要全部重绘。优先用标签而不是逐个精灵检查。旋转大图很费——在加载时旋转，别每帧转。文字对象要复用。

**下一步。**
让敌人随时间加速。加第二个玩家做成双人乒乓。把第 6 章的跳跃落地扩展成平台跳跃游戏。用 `game.every` 做倒计时和物品重生。满意之后，`python -m build` 然后 `twine upload` 发布——gamekit 自己就是这么发布的。

整个库就这些。去做点东西吧。
