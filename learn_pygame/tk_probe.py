import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\new-chat")
from gamekit import Game

print("creating tk game...")
game = Game("tk test", 200, 150, fps=60, backend="tk")
print("created, running...")
f = [0]
def update(dt):
    f[0] += 1
    if f[0] >= 30:
        print("stopping at frame", f[0])
        game.stop()
game.on_update(update)
game.run()
print("run returned, frames:", f[0])
print("DONE")
