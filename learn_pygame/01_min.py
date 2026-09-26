# pygame 对照学习 · 01：最小窗口 + Surface/blit + 事件 + Clock
# 目标：把 pygame 的四大件跑通，搞懂它为什么流畅。
# 运行后自动渲染 90 帧并保存截图退出，不弹窗卡住。

import pygame

W, H = 480, 360
FPS = 60

# --- 1. display：创建窗口（后面所有 blit 都汇到这里） ---
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("pygame min example")
clock = pygame.time.Clock()

# --- 2. Surface：一块像素内存，精灵就是这种对象 ---
# 注意这行用的是全大写（pygame 兼容旧版），等价 pygame.Surface((w, h))
box = pygame.Surface((60, 60))
box.fill((230, 60, 60))            # 填充颜色，像素直接写进这块内存
circle = pygame.Surface((50, 50), pygame.SRCALPHA)  # 带 alpha 通道的 Surface
pygame.draw.circle(circle, (255, 200, 60), (25, 25), 25)

box_x, box_y = 100.0, 100.0
box_vx, box_vy = 220.0, 150.0

running = True
frame = 0
while running:
    # --- 3. event：读输入事件（每帧一次） ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- 4. 更新逻辑（用 dt 保证不同帧率手感一致） ---
    dt = clock.tick(FPS) / 1000.0   # Clock：锁帧 + 返回上一帧耗时（秒）
    box_x += box_vx * dt
    box_y += box_vy * dt
    if box_x < 0 or box_x + 60 > W:
        box_vx = -box_vx
    if box_y < 0 or box_y + 60 > H:
        box_vy = -box_vy

    # --- 5. 绘制：先清屏，再逐个 blit（整块像素内存搬过去） ---
    screen.fill((20, 24, 32))
    screen.blit(box, (int(box_x), int(box_y)))
    screen.blit(circle, (200 + frame % 3 * 30, 60))
    pygame.display.flip()           # 把后台缓冲一次性翻到屏幕

    frame += 1
    if frame >= 90:
        running = False

# --- 验证：把画好的帧存成 PNG，不弹窗也能确认渲染结果 ---
pygame.image.save(screen, "learn_01_result.png")
print("saved learn_01_result.png, frames =", frame)
pygame.quit()
