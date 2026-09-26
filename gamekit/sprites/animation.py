"""帧动画：把多张图像按时间顺序播放。"""


class Animation:
    """一个简单的帧动画。

    :param frames: 图像路径列表（按播放顺序）
    :param fps: 播放帧率
    :param loop: 是否循环播放
    """

    def __init__(self, frames, fps=10, loop=True):
        self.frames = [str(f) for f in frames]
        self.fps = max(1, float(fps))
        self.loop = bool(loop)
        self.index = 0
        self._timer = 0.0
        self.playing = False

    @property
    def frame(self):
        """当前帧对应的图像路径；无帧时返回 None。"""
        if not self.frames:
            return None
        return self.frames[min(self.index, len(self.frames) - 1)]

    def start(self):
        self.playing = True
        return self

    def stop(self):
        self.playing = False
        return self

    def reset(self):
        self.index = 0
        self._timer = 0.0
        return self

    def update(self, dt):
        """推进动画（由 Sprite / Game 每帧调用）。"""
        if not self.playing or not self.frames:
            return
        self._timer += dt
        frame_time = 1.0 / self.fps
        while self._timer >= frame_time:
            self._timer -= frame_time
            self.index += 1
            if self.index >= len(self.frames):
                if self.loop:
                    self.index = 0
                else:
                    self.index = len(self.frames) - 1
                    self.playing = False

    def __len__(self):
        return len(self.frames)

    def __repr__(self):
        return "Animation(frames=%d, fps=%.0f, playing=%s)" % (
            len(self.frames), self.fps, self.playing)
