# gamekit

> 一个**零第三方依赖**的极简 2D 游戏库 —— 只使用 Python 标准库，API 简单到极致，功能却相当齐全。

gamekit 的目标是：**让任何人用最少的代码，最快做出一个能玩的 2D 小游戏**。不需要懂窗口、事件循环、坐标系等底层细节，一个文件就能跑起一个完整游戏。

- 🚫 **零依赖**：只用 Python 标准库（`tkinter` / 自研 GDI 渲染、`winsound` 音频），装好 Python 就能跑
- ⚡ **可插拔渲染后端**：默认 Windows 上用**自研 GDI 内核**（同场景实测约为 tkinter 的 2~3.5 倍），其他平台自动回落 tkinter；一行 `Game(backend=...)` 切换
- ✨ **极简 API**：`Game` 一个类搞定窗口、输入、精灵、碰撞、物理、音效、粒子、场景
- 🎮 **功能齐全**：精灵 / 图像 / 动画 / 碰撞 / 重力 / 音效 / 文字 / 按钮 / 进度条 / 粒子 / 场景切换
- 🪶 **轻量**：纯 Python 实现（ctypes 直接调系统 GDI），核心约 2000 行，结构清晰可读

---

## 安装

### 方式一：直接使用源码（推荐，零配置）

把 `gamekit/` 目录放到你的项目旁边，然后直接 `import gamekit`：

```bash
git clone https://github.com/yuleemoon/gamekit2d.git
cd gamekit
python examples/01_hello.py          # 直接运行示例
```

### 方式二：pip 安装

```bash
pip install gamekit2d      # 安装名是 gamekit2d，import 仍是 import gamekit
```

> 无论哪种方式都**不需要安装任何第三方包**。运行环境只需 Python 3.9+（Windows / Linux / macOS 均可，音频仅 Windows 支持，其他平台自动静默降级）。

### 渲染后端

`Game` 默认 `backend="auto"`：Windows 上自动使用**自研 GDI 高性能内核**（原生窗口 + BitBlt 双缓冲 + 矩形精灵 Surface 缓存），其他平台自动回落 tkinter。也可显式指定：

```python
Game(..., backend="gdi")    # GDI（仅 Windows）—— CPU 渲染，兼容最好
Game(..., backend="d2d")    # Direct2D GPU 加速（仅 Windows + Python 3.13）
Game(..., backend="d3d11")   # D3D11 GPU 加速（仅 Windows + Python 3.13）—— 最快
Game(..., backend="tk")     # tkinter（跨平台保底）
```

**D3D11 后端（`backend="d3d11"`）**：基于 C++ 扩展 `_d3d11.pyd` 调用 Direct3D 11 GPU API。精灵创建时注册到 C 层持久精灵数组，C 层每帧直接填充 vertex buffer，一次 `DrawIndexed` 提交所有矩形到 GPU；静态精灵位置不变时跳过顶点重建。文字 / 圆形 / 线条等 GDI 图元通过 DXGI surface DC 叠加，与 GPU 内容同屏。实测（800×600，vsync 关，真实渲染输出）：4000 个同色精灵 **214 FPS**、1000 个全异色精灵 **372 FPS**（同机 pygame 2.6.1 分别为 282 / 753 FPS）。需要 Windows 10+ 和 Python 3.13。

**Direct2D 后端（`backend="d2d"`）**：基于 C++ 扩展 `_d2d.pyd` 调用 Direct2D GPU API。矩形/椭圆/线条/多边形/圆弧全部 GPU 硬件加速，4000 个同色精灵实测 **98 FPS**。文本走 GDI 叠加。

同一套游戏代码不用改，切后端只改这一个参数。

### 场景分组与脏矩形

```python
from gamekit import Group

enemies = Group(*[game.sprite(color="red", x=i*40, y=80, width=28, height=28)
                  for i in range(10)])

@game.on_update
def wave(dt):
    enemies.move(0, 50 * dt)        # 整组移动
```

`Group` 是一组精灵的轻量容器：整组移动 / 隐藏 / 删除，不用自己写循环。精灵仍由 Game 统一渲染，Group 只做批量管理。

`Game(..., dirty=True)` 开启**脏矩形局部更新**：不整屏清屏，只把上一帧移动过的精灵旧位置刷回背景。配合 `game.sprite(..., static=True)` 标记静态元素（墙壁、砖块、UI 装饰）——它们只在第一帧画进后台缓冲，之后只要没被移动精灵压过就不再重画。

**实测结论（务必按场景选择）**：
- **适合**：少量动态元素 + 小范围移动（菜单光标、弹窗、射击子弹）——此时比整屏清屏快
- **别开**：大量精灵同时移动、或动态精灵横穿大半个屏幕——脏区会波及大量静态精灵，"恢复背景 + 重画被压静态 + Python 层相交计算"的综合开销比直接全画还高 20~30%
- 不确定就保持默认 `dirty=False`，整屏清屏用字节模板 `memmove`，1MB 只要 ~0.1ms，已经足够快

仅 GDI 后端有效。

---

## 快速上手

这是你能写出的最短游戏 —— **40 秒学会**：

```python
from gamekit import Game, Key

# 1. 创建游戏
game = Game(title="我的第一个游戏", width=800, height=600, fps=60)

# 2. 创建精灵（一个红色矩形）
player = game.sprite(color="red", x=400, y=300, width=60, height=40)

# 3. 绑定按键
@game.on_key(Key.LEFT)
def left():
    player.vx = -300

@game.on_key(Key.RIGHT)
def right():
    player.vx = 300

@game.on_key(Key.SPACE)
def stop():
    player.vx = 0

# 4. 启动游戏
game.run()
```

运行后：按 ← → 移动方块，按空格停下。**一个可玩的游戏就完成了。**

---

## Camera 相机 + 视口裁剪

大地图卷轴游戏必备，把世界坐标和屏幕坐标分开：

```python
game.camera_x = 1200   # 世界坐标左上角对应屏幕 (0,0)
game.camera_y = 400
```

设置后所有精灵绘制自动按偏移转换，**完全在屏幕外的精灵直接跳过不画**。4000 个精灵分布在 3200×2400 大地图、相机扫过只画屏幕内几十个，实测 **190 FPS**（对比全画 38 FPS，5 倍提升）——这才是大地图性能的真正解法。

## Tilemap 关卡

从字符串数组快速铺一整关（打砖块 / 平台游戏）：

```python
MAP = [
    "##########",
    "#........#",
    "#..SS....#",
    "##########",
]
game.tilemap(MAP, tile_size=32,
             tile_defs={"#": "#4488ff", "S": "#ff4444"})
```

未在 `tile_defs` 里的字符（如 `.`）视为空气。生成的瓦片自动 `static=True`，配合 camera 只画屏幕内。

## 跨平台音频

- Windows：标准库 `winsound` 播放 WAV
- macOS / Linux：自动调系统播放器（`afplay` / `paplay` / `aplay`），不装第三方包
- 探测不到播放器时静默降级，游戏不崩

---

## 功能总览

| 功能 | 说明 | 快速示例 |
|---|---|---|
| 🖼 精灵 | 图像 / 纯色 / 圆形，位置速度、旋转缩放 | `game.sprite("player.png", x=100, y=100)` |
| ⌨️ 键盘 | 按下 / 抬起 / 持续按住 | `@game.on_key(Key.SPACE)` |
| 🖱 鼠标 | 移动 / 点击 / 滚轮 | `@game.on_mouse_click` |
| 💥 碰撞 | 矩形 + 圆形，自动检测进入瞬间 | `@game.on_collide(player, "coin")` |
| 🌍 物理 | 重力、摩擦、反弹、屏幕边界 | `sprite.gravity_scale = 1.0` |
| 🎞 动画 | 多帧图像循环播放 | `sprite.play(["a.png", "b.png"], fps=8)` |
| 🔊 音频 | WAV 音效 / 循环背景乐 | `game.sound("hit.wav").play()` |
| 📝 文字 | 任意字体 / 字号 / 加粗 | `game.text("得分 0", x=30, y=30)` |
| 🔘 UI | 按钮（悬停高亮）、进度条 | `game.button("开始", on_click=fn)` |
| ✨ 粒子 | 爆炸 / 火花 / 飘雪 | `game.burst(x, y, count=40)` |
| 🎬 场景 | 菜单 / 关卡 / 结束画面切换 | `game.switch_scene(MyScene())` |
| ⏱ 定时器 | 延迟调用 / 周期调用 | `game.every(0.5, fn)` |

---

## 完整示例：收集金币

一个集精灵、物理、碰撞、粒子、计分于一体的微型游戏（约 30 行）：

```python
from gamekit import Game, Key

game = Game(title="收集金币", width=800, height=600, fps=60)
game.bg_color = "#141a24"
game.gravity = 600

# 玩家（受重力）
player = game.sprite(color="#4ac0f0", x=400, y=300, width=44, height=44)
player.gravity_scale = 1.0
player.keep_on_screen = True

# 地面
ground = game.sprite(color="#2a3342", x=400, y=580, width=800, height=40)

# 金币
score = [0]
score_text = game.text("金币：0", x=400, y=30, size=24, bold=True)
coin_n = [0]

def spawn_coin():
    coin_n[0] += 1
    return game.sprite(color="#ffd700", x=60 + (coin_n[0] * 61) % 680,
                       y=400 + (coin_n[0] * 23) % 130,
                       width=26, height=26, shape="circle", tag="coin")

for _ in range(8):
    spawn_coin()

@game.on_key(Key.SPACE)
def jump():
    if player.bottom >= ground.top - 2:
        player.vy = -420

@game.on_key_hold(Key.LEFT)
def move_left():
    player.vx = -260

@game.on_key_hold(Key.RIGHT)
def move_right():
    player.vx = 260

@game.on_key(Key.ESCAPE)
def quit_game():
    game.stop()

@game.on_collide(player, ground)
def land(p, g):
    if p.vy > 0:                      # 只在向下落时落地
        p.y = g.top - p.height / 2
        p.vy = 0

@game.on_collide(player, "coin")
def collect(p, c):
    c.remove()
    score[0] += 1
    game.burst(c.x, c.y, count=18, colors=("gold", "white", "orange"))
    score_text.set("金币：%d" % score[0])

game.run()
```

---

## 运行示例小游戏

项目自带 4 个由浅入深的完整示例（`examples/` 目录）：

```bash
python examples/01_hello.py        # 最小游戏：反弹小球 + 暂停/变色
python examples/02_pong.py         # 双人乒乓球（键盘对战）
python examples/03_breakout.py     # 打砖块（完整小游戏：场景/UI/粒子/计分/生命）
python examples/04_sprite_image.py # 图像精灵：旋转/缩放/帧动画
python examples/05_space_shooter.py# 太空射击（综合实战：键盘/碰撞/粒子/场景）
```

> 使用图像精灵的示例请先运行 `python examples/make_assets.py` 生成素材。

---

## 📖 完整教程

想从零系统学习？请看 **[TUTORIAL.md](TUTORIAL.md)** —— 13 章手把手教程，
从"第一个窗口"到"完整太空射击游戏"，每章代码都可直接运行。

---

## API 速查

### Game（游戏）

```python
Game(title="标题", width=800, height=600, fps=60, bg_color="#14141a")
game.run() / game.stop()
game.sprite(...)      # 创建精灵
game.text(...)        # 创建文字
game.button(...)      # 创建按钮
game.progress_bar(...)# 创建进度条
game.sound(path)      # 加载音效
game.music(path)      # 加载循环背景乐
game.particles(...)   # 粒子系统
game.burst(x, y, ...) # 一次粒子爆发
game.add_scene(s) / game.switch_scene(s)   # 场景管理
game.after(sec, fn) / game.every(sec, fn)  # 定时器
game.gravity          # 全局重力（像素/秒²）
game.dt / game.time   # 帧耗时 / 累计时间
game.is_key_down(key) # 按键是否按住
game.find(tag)        # 按标签查找精灵
```

### 事件装饰器

```python
@game.on_update                    # 每帧更新  fn(dt)
@game.on_key(Key.SPACE)            # 按键按下  fn()
@game.on_key_up(Key.SPACE)         # 按键抬起  fn()
@game.on_key_hold(Key.LEFT)        # 按住持续  fn(dt)
@game.on_mouse_click               # 左键点击  fn(x, y)
@game.on_mouse_move                # 鼠标移动  fn(x, y)
@game.on_mouse_down / up           # 按下/抬起 fn(x, y, button)
@game.on_mouse_wheel               # 滚轮      fn(delta, x, y)
@game.on_collide(a, b)             # 碰撞进入  fn(a, b)  a/b 可为精灵或标签
```

### Sprite（精灵）

```python
s = game.sprite(image="a.png" | color="red", x=0, y=0,
                width=40, height=40, shape="rect|circle", tag="enemy")
s.x / s.y / s.vx / s.vy            # 位置与速度（像素/秒）
s.move(dx, dy) / s.move_to(x, y)
s.set_scale(f) / s.set_angle(deg)  # 缩放 / 旋转（图像精灵）
s.play([f1, f2], fps=8, loop=True) # 帧动画
s.hide() / s.show() / s.remove()
s.collides_with(other)             # 是否碰撞
s.bounce_off(other)                # 按重叠方向反弹
s.gravity_scale / s.friction / s.bounce / s.keep_on_screen
s.on_update = lambda dt: ...       # 单精灵每帧逻辑
```

### Key（按键常量）

```python
Key.SPACE / Key.UP / Key.DOWN / Key.LEFT / Key.RIGHT
Key.ENTER / Key.ESC / Key.TAB / Key.BACKSPACE
Key.SHIFT / Key.CTRL / Key.ALT
Key.A ~ Key.Z  /  Key.F1 ~ Key.F12
```

也可以直接传字符串：`"space"`、`"a"`、`"F5"`（大小写均可）。

---

## 项目结构

```
gamekit/
├── gamekit/
│   ├── core/        # 核心引擎：Game 主类、场景、事件、按键
│   ├── render/      # 自研渲染层：Surface/Window（GDI 内核）+ 后端接口
│   ├── sprites/     # 精灵、图像处理（自研缩放/旋转）、帧动画
│   ├── physics/     # 碰撞检测（矩形/圆形）
│   ├── audio/       # WAV 音效（winsound）
│   ├── ui/          # 文字、按钮、进度条
│   ├── fx/          # 粒子系统
│   └── utils/       # 颜色、向量工具
├── examples/        # 5 个完整示例 + 素材生成脚本
├── tests/           # 单元测试 + GUI 冒烟测试
├── pyproject.toml   # 发布配置（零依赖）
└── README.md
```

---

## 已知限制（标准库方案的能力边界）

由于坚持零第三方依赖，有以下取舍，**请按需评估**：

| 能力 | 限制 | 说明 |
|---|---|---|
| 音频 | 仅 `.wav`，仅 Windows，一次一个 | 标准库 `winsound` 的能力边界；其他平台自动静默 |
| 图像格式 | PNG / GIF / PPM / BMP | 不支持 JPG（Tk 无解码器），可用 PNG 替代 |
| 旋转/缩放 | 最近邻算法，大图较慢 | 适合 200×200 以下的小图，在加载时调用一次 |
| 渲染性能 | GDI 约为 tkinter 的 2~3.5 倍；D3D11 后端 214 FPS | 同场景实测（32×32 矩形，800×600，vsync 关）：GDI 4000 个 ~60 FPS；D2D 4000 个 ~98 FPS；D3D11 4000 个同色 ~214 FPS、1000 个异色 ~372 FPS；pygame 282~753 FPS。tkinter 跨平台保底 |

---

## 测试

```bash
python -m unittest discover -s tests -p "test_*.py"   # 单元测试（碰撞/颜色/向量/按键）
python tests/run_selftest.py                          # GUI 冒烟测试（自动运行 120 帧）
```

---

## 许可

[MIT](LICENSE) © gamekit contributors

用游戏kit，做个游戏吧 🎮
