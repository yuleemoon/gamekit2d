# gamekit — pygame, minus the boilerplate

You want to make a 2D game, but every time you open the pygame docs you spend
an hour setting up a window and an event loop before anything moves on screen.

gamekit is the opposite. One class, a handful of methods, zero third-party
dependencies (it runs on the standard library: a self-made GDI renderer on
Windows / tkinter elsewhere, and winsound for audio). You still get
everything pygame gives you — sprites, input, collisions, images, fonts,
sound, shapes, timing, scenes — but the code you write is maybe a third of
the size.

This tutorial goes end to end: the loop, sprites, movement, input, collision,
text, UI, shapes, images, sound, particles, scenes, and a full game at the end.
Every chapter has runnable code. Install it with:

```
pip install gamekit2d
```

Python 3.9 or newer. Nothing else.

> **Rendering backends.** `Game(backend="auto")` is the default: on Windows it
> uses gamekit's own GDI kernel (native window, double-buffered BitBlt, an
> order of magnitude faster than tkinter — 1000+ colored sprites stay smooth),
> and falls back to tkinter everywhere else. You can force either with
> `backend="gdi"` or `backend="tk"`. Game code doesn't care which one is
> running; only that one parameter changes.

---

## Chapter 0 — What gamekit covers

Here's the honest map from pygame to gamekit. If you've used pygame, this is
the cheat sheet you want. If you haven't, skim it and move on — the rest of
the tutorial explains each row.

| pygame | gamekit | Notes |
|---|---|---|
| `pygame.display.set_mode` | `Game(width=, height=)` | Pass `fps=` too |
| `pygame.display.set_caption` | `Game(title=)` | |
| `pygame.event.get()` / `KEYDOWN` | `@game.on_key(Key.X)` | Decorator, fires once per press |
| `pygame.key.get_pressed()` | `game.is_key_down(Key.X)` | Hold-state check inside `on_update` |
| `KEYUP` | `@game.on_key_up(Key.X)` | |
| `MOUSEMOTION` / `MOUSEBUTTONDOWN` | `@game.on_mouse_move` / `on_mouse_down` | |
| `MOUSEBUTTONUP` / `mouse.get_pos` | `@game.on_mouse_up` / `game.mouse_x, game.mouse_y` | |
| `pygame.Sprite` + `pygame.sprite.Group` | `game.sprite()` + `tag=` | Tags replace groups |
| `pygame.sprite.collide_rect` | `sprite.collides_with(other)` | |
| `pygame.sprite.collide_circle` | same call | Circles auto-detect circles |
| `pygame.draw.rect` | `game.sprite(color=..., shape="rect")` | Solid rectangle |
| `pygame.draw.circle` | `game.sprite(color=..., shape="circle")` | Solid circle |
| `pygame.draw.line` | `game.line(...)` | |
| `pygame.draw.polygon` | `game.polygon(...)` | |
| `pygame.draw.ellipse` | `game.ellipse(...)` | |
| `pygame.draw.arc` | `game.arc(...)` | |
| `pygame.draw.lines` | `game.polygon(..., outline=...)` | Open shapes become outlines |
| `pygame.image.load` | `game.sprite("file.png")` | PNG / GIF / BMP / PPM. No JPG |
| `pygame.transform.scale` | `sprite.set_scale(1.5)` | |
| `pygame.transform.rotate` | `sprite.set_angle(45)` | Degrees |
| `pygame.transform.flip` | `sprite.flip(horizontal=True, vertical=False)` | |
| `pygame.image.save` | `sprite.save_image("out.ppm")` | PPM / GIF / BMP |
| `pygame.font.Font.render` | `game.text(...)` + `.set(...)` | Update text, don't recreate it |
| `pygame.mixer.Sound.play` | `game.sound("hit.wav").play()` | WAV only, Windows only |
| `pygame.mixer.music` | `game.music("bgm.wav")` | Loops by default |
| `pygame.time.Clock.tick` | `fps=60` on the `Game` | Handled for you |
| `pygame.time.get_ticks` | `game.time` | Seconds, not ms |
| `pygame.mask` | `pixel_collide(a, b)` | Pixel-perfect, not a full mask API |
| `pygame.math.Vector2` | `Vec2` | |
| `pygame.Rect` | `sprite.left/right/top/bottom` | Geometry is on the sprite |
| `pygame.Color` | `Color`, named constants | |
| `pygame.QUIT` | handled automatically | Closing the window stops the game |
| `pygame.joystick` | — | No gamepad support in the stdlib |
| `pygame.camera` | — | No webcam support in the stdlib |
| `pygame.Surface` + `blit` | sprites, or the `on_draw` hook | You don't manage surfaces |

Two things to say up front, because they'll save you time:

1. **gamekit is Windows-first for audio.** tkinter runs everywhere, but sound
   (winsound) only works on Windows. On Linux or macOS, `play()` prints a
   message and the game keeps running. That's the price of zero dependencies.
2. **No gamepad, no webcam.** The standard library has neither. If your game
   needs a joystick, keep pygame. For everything else on that table, read on.

---

## Chapter 1 — Your first window

Create `hello.py`:

```python
from gamekit import Game

game = Game(title="Hello", width=640, height=480, fps=60)
game.run()
```

Run `python hello.py`. A dark window opens and stays. That's a game now —
the loop is running, drawing the background 60 times a second.

The `Game` object is the whole library. You create sprites through it,
register callbacks on it, and start everything with one `run()` call.

---

## Chapter 2 — The game loop

Every game is a loop. Each pass does three things:

```
   ┌────────────────┐
   │  1. read input  │──┐
   └────────────────┘  │
            │           │
            ▼           │
   ┌────────────────┐   │
   │  2. update world│   │
   └────────────────┘   │
            │           │
            ▼           │
   ┌────────────────┐   │
   │  3. draw frame  │   │
   └────────────────┘   │
            │           │
            └───────────┘
```

- Read what the player pressed.
- Move things, check collisions, update the score.
- Draw everything.

gamekit runs this loop for you at your `fps`. All you write is the "update
world" part, and even that is optional at first.

Three values you'll use constantly:

- `game.time` — seconds since the game started (like `pygame.time.get_ticks`
  but in seconds).
- `game.dt` — how long the last frame took, in seconds. You get it passed to
  every update callback.
- `fps` — how many times a second the loop runs.

The rule that keeps your game sane across different machines:

**Always think in pixels per second, never pixels per frame.**

Don't write "move 10 pixels every frame". Write "move 300 pixels per second"
and multiply by `dt`. Then 60 fps and 30 fps feel identical. gamekit's built-in
velocity does this for you, and every example follows the rule.

---

## Chapter 3 — Sprites

A sprite is anything you see on screen. The player, enemies, bullets, coins —
they're all sprites.

```python
from gamekit import Game

game = Game(title="Sprites", width=640, height=480)

# A red square, centre at (320, 240)
box = game.sprite(color="red", x=320, y=240, width=80, height=80)

# A gold circle
ball = game.sprite(color="gold", x=100, y=100, width=40, height=40, shape="circle")

game.run()
```

Coordinates work the way you expect from pygame: (0, 0) is the top-left
corner, x grows right, y grows down. `x` and `y` are the sprite's centre.

Useful properties:

```python
player = game.sprite(color="skyblue", x=100, y=100, width=60, height=60,
                     shape="rect", tag="player", layer=0)

player.x, player.y          # position (centre)
player.vx, player.vy        # velocity, pixels per second
player.width, player.height # size
player.visible              # True/False
player.layer                # draw order, bigger is on top
player.tag                  # label, used to match groups
player.solid                # whether it takes part in collisions
```

Two shapes exist: `"rect"` (default) and `"circle"`. A circle sprite also
collides as a circle, not as a box around the circle. For image sprites,
`shape` is ignored — the image defines the size.

`tag` is your group. In pygame you'd make a `Group` for bullets and iterate
it. Here you give every bullet `tag="bullet"` and match them all at once:

```python
enemies = game.find("enemy")   # list of sprites with this tag
```

---

## Chapter 4 — Movement

Set a velocity and the sprite moves itself. No manual `x += speed` needed.

```python
game = Game(width=640, height=480)

ball = game.sprite(color="gold", x=320, y=240, width=30, height=30, shape="circle")
ball.vx = 200     # 200 px/s to the right
ball.vy = 150     # 150 px/s down
ball.bounce = 1.0 # bounce off screen edges, 1.0 = perfectly elastic

game.run()
```

`bounce` takes 0 to 1. `0.5` means the ball loses half its speed on each
bounce. Set it to `0` (the default) and the ball flies off screen forever.

### Physics flags

```python
game.gravity = 500          # px/s², affects sprites with gravity_scale > 0

ball = game.sprite(color="cyan", x=320, y=100, width=20, height=20, shape="circle")
ball.gravity_scale = 1.0    # 0 = ignore gravity, 2.0 = falls twice as fast
ball.bounce = 0.8           # bounce off the floor
ball.friction = 0.5         # velocity decays over time
ball.keep_on_screen = True  # stop at the edges instead of bouncing
```

Use either `bounce` or `keep_on_screen`, not both — one bounces, the other
stops.

### Manual control

Velocity is the fast path. When you need real control — a curve, follow the
mouse, a sine wave — move the sprite yourself inside `on_update`:

```python
@game.on_update
def tick(dt):
    player.x += 300 * dt              # constant rightward speed

    player.x = game.mouse_x           # follow the mouse
    player.y = game.mouse_y

    import math
    player.x = 320 + math.cos(game.time * 2) * 150   # orbit
    player.y = 240 + math.sin(game.time * 2) * 150
```

`move(dx, dy)` shifts relative, `move_to(x, y)` jumps to a point,
`look_at(other)` points the sprite at a sprite or a `(x, y)` tuple.

---

## Chapter 5 — Input

### Keys: fire once

`@game.on_key(Key.X)` runs the callback once when the key is pressed.

```python
from gamekit import Game, Key

@game.on_key(Key.SPACE)
def jump():
    player.vy = -400

@game.on_key(Key.ESC)
def quit_game():
    game.stop()

@game.on_key("a")       # letters work as plain strings
def move_left():
    player.vx = -300
```

Useful key constants: `Key.SPACE`, `Key.UP/DOWN/LEFT/RIGHT`, `Key.ENTER`,
`Key.ESC`, `Key.TAB`, `Key.SHIFT/CTRL/ALT`, `Key.F1`–`Key.F12`, plus `"a"`–
`"z"` and `"0"`–`"9"` as strings.

### Keys: hold (the one you'll use most)

`@game.on_key_hold(Key.X)` fires every frame while the key is held, and the
callback gets `dt`. This is the right tool for movement:

```python
@game.on_key_hold(Key.LEFT)
def left():
    player.vx = -300

@game.on_key_hold(Key.RIGHT)
def right():
    player.vx = 300

@game.on_key_up(Key.LEFT)     # fire when released
def stop_left():
    player.vx = 0
```

The alternative, which some people find cleaner, is to check the held state
inside `on_update`:

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

### Mouse

```python
@game.on_mouse_click       # left click, fn(x, y)
def click(x, y):
    print("clicked", x, y)

@game.on_mouse_move        # fn(x, y)
@game.on_mouse_down        # any button, fn(x, y, button)
@game.on_mouse_up          # any release, fn(x, y, button)
@game.on_mouse_wheel       # fn(delta, x, y)
```

Current position is always readable: `game.mouse_x`, `game.mouse_y`. A paddle
that follows the mouse is three lines:

```python
@game.on_update
def tick(dt):
    paddle.x = game.mouse_x
```

---

## Chapter 6 — Collision

Collision detection is just the question "do these two shapes overlap?"

- **Rectangles**: do their edges cross?
- **Circles**: is the centre distance smaller than the radii added?

gamekit draws the correct answer automatically — two circle sprites collide
as circles, everything else as rectangles.

### Check manually

```python
if player.collides_with(enemy):
    print("hit")

if player.contains(x, y):      # is a point inside the sprite?
    print("pointer on player")

d = player.distance_to(enemy)  # centre distance
```

### Automatically, with a callback

`@game.on_collide(a, b)` fires **once, the moment two objects start
touching** — not every frame. That's exactly what you want for "ate a coin"
or "bullet hit an enemy".

```python
# Two specific sprites
@game.on_collide(player, coin)
def collect(p, c):
    c.remove()

# A sprite against a tag — matches every sprite tagged "coin"
@game.on_collide(player, "coin")
def collect(p, c):
    c.remove()

# Tag against tag
@game.on_collide("bullet", "enemy")
def hit(bullet, enemy):
    bullet.remove()
    enemy.remove()
```

That last one is how you wire up shooting without ever touching the sprites
directly. `"bullet"` and `"enemy"` are both tags.

### Bounce off something

For breakout / pong, `bounce_off` reverses the right axis and pushes the
sprite out of the overlap, so it doesn't get stuck inside the other object:

```python
@game.on_collide(ball, brick)
def hit(ball, brick):
    brick.remove()
    ball.bounce_off(brick)   # flips vx or vy depending on which side hit
```

### Pixel-perfect collision

Rectangles lie at the corners — a round coin touching a square corner counts
as a hit even though the pixels don't touch. When that matters, use
`pixel_collide` (the stand-in for `pygame.mask`):

```python
from gamekit import pixel_collide

if pixel_collide(player, coin):   # both must be image sprites
    coin.remove()
```

It compares actual pixels in the overlap: both images must have a non-
transparent pixel at the same spot. If a sprite has no image, it falls back
to a rectangle check automatically.

### A complete jump-and-land

```python
game.gravity = 600
player.gravity_scale = 1.0
ground = game.sprite(color="gray", x=320, y=580, width=640, height=40)

@game.on_collide(player, ground)
def land(p, g):
    if p.vy > 0:                 # only land while falling
        p.y = g.top - p.height / 2
        p.vy = 0
```

---

## Chapter 7 — Text and fonts

```python
title = game.text("Score: 0", x=320, y=30, size=28, color="white",
                  bold=True, anchor="center")
```

- `x, y` — position.
- `size` — point size. `color` — well, the color.
- `font` — family, defaults to a font with solid CJK support.
- `bold=True`, `italic=True` — both available.
- `anchor` — `"center"` (default), `"nw"` (top-left), `"n"` (top-centre), etc.

### Update the text, don't recreate it

This is the one habit that matters. `set()` updates in place:

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

Calling `game.text()` every frame to "update" text creates objects and runs
slow. One text object, one `.set()` per change.

---

## Chapter 8 — UI widgets

### Button

```python
game.button("Start", x=320, y=300, width=180, height=52,
            on_click=start_game)     # fn(button)

def start_game(button):
    button.text = "Running"
```

Buttons highlight on hover and fire `on_click` on release. That's all.

### Progress bar

```python
hp = game.progress_bar(x=320, y=30, width=300, height=20,
                       value=100, max_value=100, color="lime")

hp.set_value(60)      # converts to a ratio automatically
```

Good for health bars, XP bars, timers.

---

## Chapter 9 — Drawing shapes (pygame.draw)

Sprites are solid rectangles and circles. When you need a line, a polygon, an
ellipse, or an arc, use the shape functions. They're managed like sprites —
movable, layerable, removable — but they stay visual: **shapes don't
collide**. If it needs to collide, make it a sprite.

```python
# Line from (x1, y1) to (x2, y2)
game.line(x1=100, y1=400, x2=300, y2=400, color="white", width=3)

# Polygon from a list of points
game.polygon([(400, 400), (440, 350), (480, 400)],
             color="violet", outline=None)

# Ellipse (or circle) centred at (x, y)
game.ellipse(x=120, y=250, width=80, height=40, color="skyblue")

# Arc of an ellipse — start and extent in degrees, 0 = right, clockwise
game.arc(x=560, y=250, width=60, height=60,
         start=0, extent=270, color="lime", width_px=3)
```

Every shape returns an object with `x, y, vx, vy, visible, layer, tag` and
`remove()`. Give a line a velocity and it drifts. Give a polygon a tag and
you can find it later.

---

## Chapter 10 — Images and animation

### Load, scale, rotate, flip

```python
player = game.sprite("player.png", x=320, y=240)  # path as first arg
player.set_scale(1.5)     # 1.5x
player.set_angle(45)      # 45 degrees
player.flip(horizontal=True)   # mirror it
player.set_image("other.png")  # swap image
```

Supported formats: **PNG, GIF, BMP, PPM**. No JPG — tkinter can't read it.

Rotation and non-integer scaling resample pixels on the fly. Fine for a
handful of sprites at load time; slow if you re-rotate a huge image every
frame. Keep that in mind.

### Save an image

```python
player.save_image("out.ppm")    # pygame.image.save
```

Writes the sprite's current image to a file. PPM, GIF, and BMP work. PNG
doesn't, because the standard library can't write it.

### Frame animation

```python
# Play two frames of a coin flashing, 4 fps, looping
coin = game.sprite("coin1.png", x=320, y=200)
coin.play(["coin1.png", "coin2.png"], fps=4, loop=True)

coin.stop_animation()
```

The example assets are generated by `examples/make_assets.py`, which uses
nothing but the standard library to draw PNGs.

---

## Chapter 11 — Sound

```python
# Play a sound once
hit = game.sound("hit.wav")
hit.play()

# Looping background music
music = game.music("bgm.wav")    # same as game.sound(path, loop=True)

music.stop()
```

That's the whole API. The constraints are real, so repeat them:

- **WAV only.** The standard library decodes wav and nothing else.
- **Windows only.** `winsound` is Windows. Elsewhere, `play()` prints a note
  and continues.
- **One sound at a time.** `winsound` plays a single audio. Music and sound
  effects can't overlap. If you need layered audio, pygame is the better tool.

For a quick effect, generate a small WAV with Python's `wave` module and play
it. No asset pipeline needed.

---

## Chapter 12 — Particles

gamekit's own extra. Explosions, sparks, confetti — cheap and useful.

```python
# One-shot explosion
game.burst(x=320, y=240, count=40,
           colors=("orange", "yellow", "red"),   # picked at random
           speed=(50, 260),        # initial speed range, px/s
           life=(0.4, 1.5))        # lifetime range, seconds

# A particle system you can trigger repeatedly
stars = game.particles(x=320, y=200, count=30, colors=("white", "cyan"))
stars.burst()              # fire a batch
stars.burst(count=60)      # or specify how many
```

A burst in a collision callback is the fastest way to make a hit feel good:

```python
@game.on_collide("bullet", "enemy")
def hit(bullet, enemy):
    game.burst(enemy.x, enemy.y, count=20, colors=("orange", "yellow"))
    bullet.remove()
    enemy.remove()
```

---

## Chapter 13 — Scenes

Real games have a menu, a play screen, and a game-over screen. That's what
`Scene` is for. A scene owns its sprites, text, buttons, and particles;
switching scenes swaps them out.

```python
from gamekit import Game, Scene

class MenuScene(Scene):
    def on_enter(self, game):          # build the scene here
        game.text("My Game", x=320, y=200, size=48, bold=True)
        game.button("Start", x=320, y=320, on_click=self.start)

    def start(self, button):
        self.game.switch_scene(GameScene())

    def on_exit(self):                 # leave the scene here
        self.clear()

class GameScene(Scene):
    def on_enter(self, game):
        self.player = game.sprite(color="cyan", x=320, y=400, width=50, height=50)

    def on_update(self, dt):
        # this scene's per-frame logic
        ...

game = Game(width=640, height=480)
game.switch_scene(MenuScene())
game.run()
```

Things worth knowing about scenes:

- `on_enter` creates everything for that scene. `on_exit` cleans it up.
- Collision callbacks are wiped on every scene switch, so register the ones
  you need inside `on_enter`. Key, mouse, and update callbacks are global and
  survive scene changes.
- `game.switch_scene(Scene)` calls old `on_exit`, then new `on_enter`.

---

## Chapter 14 — Vec2 and colors

Two small helpers for the math you'll actually do.

### Vec2

```python
from gamekit import Vec2

v = Vec2(3, 4)
v.length()          # 5.0
v.normalized()      # unit vector
v2 = Vec2.from_angle(45, 10)   # 10 px/s at 45 degrees
v.rotated(90)       # rotate a vector
v.dot(other)        # dot product
```

Useful for firing at an angle, or pointing a bullet at the player:

```python
direction = (Vec2(enemy.x, enemy.y) - Vec2(player.x, player.y)).normalized()
bullet.vx = direction.x * 300
bullet.vy = direction.y * 300
```

### Color

```python
from gamekit import RED, GOLD, to_color, mix

sprite.color = RED                 # a named constant (a Color object)
sprite.color = (255, 100, 0)       # an (r, g, b) tuple
sprite.color = "#ff6400"           # a hex string
sprite.color = mix("red", "blue", 0.5)   # halfway between
```

Any API that takes a color accepts all three forms. `Color(r, g, b)` gives
you `.hex` and `.tuple` if you need them.

---

## Chapter 15 — The full game: space shooter

Everything above, in one file. Left/right to move, space to shoot (hold for
auto-fire), kill enemies for points, don't get hit.

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
        self.shoot_cd = 0.0        # fire cooldown
        self.spawn_timer = 0.0     # enemy spawn timer

    def on_enter(self, game):
        self.game = game
        game.bg_color = "#0a0e18"

        self.player = game.sprite(color="#4ac0f0", x=W // 2, y=H - 60,
                                  width=50, height=40)
        self.player.keep_on_screen = True

        self.score_text = game.text("Score 0", x=90, y=26, size=20, bold=True)
        self.lives_text = game.text("Lives 3", x=W - 90, y=26, size=20, bold=True)

        # Register collisions here — they're wiped on scene switch
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

        if self.game.is_key_down(Key.SPACE):   # hold to auto-fire
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

Save it as `space_shooter.py` and run it. Every line uses something from the
chapters above: sprites, held-key input, tag collisions, particles, text,
scenes, buttons.

---

## Chapter 16 — FAQ and gotchas

**The window closes instantly.**
Add an ESC handler, or end your script with `input()` to hold the window open.

**Text updates are slow.**
You're calling `game.text()` in a loop. Create once, call `.set()` after.

**A sprite doesn't move.**
Did you set `vx`/`vy`, or modify `x`/`y` in `on_update`? If neither, nothing
moves. Also check it's `visible`.

**A collision never fires.**
Both sprites need `solid=True` (default) and `visible=True` (default). And
remember `on_collide` fires once per entry, not per frame — a pair that stays
touching won't re-fire until they separate and touch again.

**Text shows boxes or wrong glyphs.**
Default font handles CJK; if a custom `font=` can't render a glyph, switch
back to the default or a font you know is installed.

**An image won't load.**
PNG, GIF, BMP, PPM only. No JPG. Check the path and that the file exists.

**Performance tips.**
A few hundred solid sprites run smooth; a few thousand will drop frames,
because every frame redraws everything. Prefer tags over per-sprite checks.
Rotating large images is expensive — rotate at load time, not per frame.
Reuse text objects.

**Next steps.**
Speed the enemies up over time. Add a second player to make a two-player
pong. Turn the jump-and-land from chapter 6 into a platformer. Use `game.every`
for countdowns and item respawns. When you're happy, `python -m build` and
`twine upload` it — gamekit itself is published exactly that way.

That's the whole library. Go make something.
