# learn_pygame/bench_leak.py
# 连续创建/销毁多个 GDI Game，监控进程 GDI 对象和 USER 对象数，查泄漏。
import sys, time, ctypes
sys.path.insert(0, r"C:\Users\Administrator\Desktop\new-chat")
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
GR_GDIOBJECTS = 0
GR_USEROBJECTS = 1

def gdi_count():
    return user32.GetGuiResources(kernel32.GetCurrentProcess(), GR_GDIOBJECTS)

def user_count():
    return user32.GetGuiResources(kernel32.GetCurrentProcess(), GR_USEROBJECTS)

from gamekit import Game

print("启动后基线: GDI=%d  USER=%d" % (gdi_count(), user_count()))
for i in range(6):
    g = Game("leak %d" % i, 320, 240, fps=999, backend="gdi")
    for j in range(20):
        g.sprite(color="#%06x" % (j*0x11111), x=(j*13)%280, y=(j*17)%200,
                 width=20, height=20)
    frames = [0]
    t0 = time.perf_counter()
    def update(dt):
        frames[0] += 1
        if time.perf_counter() - t0 >= 0.3:
            g.stop()
    g.on_update(update)
    g.run()
    g = None
    print("第 %d 个 Game 关闭后: GDI=%d  USER=%d  (frames=%d)"
          % (i+1, gdi_count(), user_count(), frames[0]))
print("完成。如果 GDI/USER 数逐次增长 = 有泄漏")
