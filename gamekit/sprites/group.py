"""Group —— 一组精灵的轻量容器（pygame.sprite.Group 的简化版）。

Group 不接管渲染：精灵仍由 Game 统一管理、统一绘制。它只是给你一个
批量操作一组精灵的工具——整组移动、整组隐藏、整组删除、整组更新，
不用自己写循环。

::

    enemies = Group(
        game.sprite(color="red", x=100, y=100, width=30, height=30),
        game.sprite(color="red", x=200, y=100, width=30, height=30),
    )

    @game.on_update
    def move_enemies(dt):
        enemies.move(0, 40 * dt)      # 整组下落
        for e in enemies:
            if e.y > game.height:
                e.kill()               # 出屏删除
"""


class Group:
    """一组精灵的批量容器。

    接收任意数量的 Sprite（或带 ``x/y/visible/kill`` 接口的对象）。
    之后可以整组移动、隐藏、删除。
    """

    def __init__(self, *sprites):
        self.sprites = [s for s in sprites if s is not None]

    # ---- 增删 ----
    def add(self, *sprites):
        """加入一个或多个精灵（自动去重）。"""
        for s in sprites:
            if s is not None and s not in self.sprites:
                self.sprites.append(s)
        return self

    def remove(self, sprite):
        """只从组里摘掉（不删除精灵本身）。"""
        if sprite in self.sprites:
            self.sprites.remove(sprite)
        return self

    def kill(self):
        """整组从游戏里删除（每个精灵调用 ``kill()``）。"""
        for s in self.sprites:
            if hasattr(s, "kill"):
                s.kill()
            elif hasattr(s, "remove"):
                s.remove()
        self.sprites.clear()
        return self

    def clear(self):
        """清空组引用（不删除精灵）。"""
        self.sprites.clear()
        return self

    # ---- 批量操作 ----
    def move(self, dx, dy):
        """整组平移 ``(dx, dy)`` 像素。"""
        for s in self.sprites:
            s.x += dx
            s.y += dy
        return self

    def set_visible(self, visible):
        """整组显示/隐藏。"""
        for s in self.sprites:
            s.visible = bool(visible)
        return self

    def update(self, dt):
        """对组里每个精灵调用它的 ``update(dt)``（如果定义了）。"""
        for s in self.sprites:
            if hasattr(s, "update"):
                s.update(dt)
        return self

    # ---- 查询 ----
    def offscreen(self, game):
        """返回完全离开屏幕下边界的精灵（方便批量清理）。"""
        return [s for s in self.sprites if s.y > game.height]

    def filter(self, predicate):
        """返回满足 ``predicate(sprite)`` 的精灵新列表。"""
        return [s for s in self.sprites if predicate(s)]

    # ---- 容器协议 ----
    def __iter__(self):
        return iter(self.sprites)

    def __len__(self):
        return len(self.sprites)

    def __contains__(self, item):
        return item in self.sprites

    def __getitem__(self, index):
        return self.sprites[index]
