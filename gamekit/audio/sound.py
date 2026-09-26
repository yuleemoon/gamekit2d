"""音频模块：WAV 音效与背景音乐。

实现说明（零第三方依赖）：
- Windows：ctypes 绑 ``winmm.dll`` 的 waveOutWrite，多音效同时播放由系统混音
  （告别 winsound "一次只能放一个"）
- macOS / Linux：subprocess 调系统播放器（afplay / paplay / aplay）
- 探测不到播放器时静默降级，不影响游戏

仅支持 ``.wav``（标准库 wave 模块解码）。
"""

import os
import sys
import shutil
import subprocess

_WIN = sys.platform == "win32"
if _WIN:
    from . import winmm as _winmm
    _HAS_AUDIO = True
else:
    _HAS_AUDIO = False
    _PLAYER = None
    for cmd in (["afplay"], ["paplay"], ["aplay"]):
        if shutil.which(cmd[0]):
            _PLAYER = cmd
            _HAS_AUDIO = True
            break
    _child = None


class Sound:
    """一个 WAV 音频。

    :param path: .wav 文件路径
    :param volume: 音量 0.0 ~ 1.0（winmm 后端暂未实现音量，仅记录保留）
    :param loop: 是否循环播放
    """

    def __init__(self, path, volume=1.0, loop=False):
        if not os.path.exists(path):
            raise FileNotFoundError("音频文件不存在: %s" % path)
        if not path.lower().endswith(".wav"):
            raise ValueError(
                "gamekit 音频仅支持 .wav 文件（标准库能力限制），收到: %s" % path
            )
        self.path = path
        self.volume = max(0.0, min(1.0, float(volume)))
        self._looping = bool(loop)
        self._playing = False
        self._pcm = None
        self._info = None

    def _ensure_pcm(self):
        if self._pcm is None:
            self._pcm, sr, ch, bits = _winmm.load_wav(self.path)
            self._info = (sr, ch, bits)

    @property
    def playing(self):
        return self._playing

    def play(self, loop=None):
        """播放音频。Windows 下多个 Sound 可同时播放（系统混音）。"""
        if loop is not None:
            self._looping = bool(loop)
        if _WIN:
            try:
                self._ensure_pcm()
                sr, ch, bits = self._info
                _winmm.play_pcm(self._pcm, sr, ch, bits, loop=self._looping)
                self._playing = True
            except Exception:
                self._playing = False
            return self
        if not _HAS_AUDIO:
            return self
        global _child
        try:
            if _child is not None:
                try:
                    _child.kill()
                except Exception:
                    pass
            _child = subprocess.Popen(_PLAYER + [self.path])
            self._playing = True
        except Exception:
            self._playing = False
        return self

    def stop(self):
        """停止播放。"""
        if _WIN:
            _winmm.stop_all()
        else:
            global _child
            if _child is not None:
                try:
                    _child.kill()
                except Exception:
                    pass
                _child = None
        self._playing = False
        return self
