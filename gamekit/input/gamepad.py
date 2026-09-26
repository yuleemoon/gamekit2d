"""Windows 游戏手柄支持（ctypes 绑 winmm.dll，零第三方依赖）。

枚举 joystick 设备，每帧读摇杆位置和按钮状态。仅 Windows。
没有手柄时 ``Gamepad.connected()`` 返回 False，游戏逻辑直接跳过。
"""
import ctypes
from ctypes import wintypes
import sys

if sys.platform != "win32":
    _winmm = None
else:
    _winmm = ctypes.windll.winmm

# JOYINFOEX 标志
_JOY_RETURNP0V = 0x00000001
_JOY_RETURNP1V = 0x00000002
_JOY_RETURNP2V = 0x00000004
_JOY_RETURNP3V = 0x00000008
_JOY_RETURNX = 0x00000010
_JOY_RETURNY = 0x00000020
_JOY_RETURNZ = 0x00000040
_JOY_RETURNR = 0x00000080
_JOY_RETURNU = 0x00000100
_JOY_RETURNV = 0x00000200
_JOY_RETURNPOV = 0x00000400
_JOY_RETURNBUTTONS = 0x00000800
_JOY_RETURNALL = (_JOY_RETURNX | _JOY_RETURNY | _JOY_RETURNZ
                  | _JOY_RETURNR | _JOY_RETURNU | _JOY_RETURNV
                  | _JOY_RETURNPOV | _JOY_RETURNBUTTONS)

# 按钮掩码（1..32）
def _btn_mask(n):
    return 1 << (n - 1)


class JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("dwXpos", wintypes.DWORD),
        ("dwYpos", wintypes.DWORD),
        ("dwZpos", wintypes.DWORD),
        ("dwRpos", wintypes.DWORD),
        ("dwUpos", wintypes.DWORD),
        ("dwVpos", wintypes.DWORD),
        ("dwButtons", wintypes.DWORD),
        ("dwButtonNumber", wintypes.DWORD),
        ("dwPOV", wintypes.DWORD),
        ("dwReserved1", wintypes.DWORD),
        ("dwReserved2", wintypes.DWORD),
    ]


class Gamepad:
    """一个游戏手柄。用 ``Gamepad.detect()`` 枚举并创建。

    典型用法::

        pad = Gamepad.detect()
        if pad:
            @game.on_update
            def move(dt):
                x, y = pad.axes()
                player.x += x * 300 * dt
    """

    def __init__(self, id_=0):
        self.id = id_
        self._info = JOYINFOEX()
        self._info.dwSize = ctypes.sizeof(JOYINFOEX)
        self._info.dwFlags = _JOY_RETURNALL
        self._present = False

    @staticmethod
    def detect():
        """枚举第一个可用手柄，没有就返回 None。"""
        if _winmm is None:
            return None
        n = _winmm.joyGetNumDevs()
        for i in range(min(n, 16)):
            pad = Gamepad(i)
            if pad.poll():
                return pad
        return None

    def connected(self):
        return self._present

    def poll(self):
        """读一次当前状态。返回 True 表示手柄在线。"""
        if _winmm is None:
            return False
        rc = _winmm.joyGetPosEx(self.id, ctypes.byref(self._info))
        self._present = (rc == 0)
        return self._present

    def axes(self):
        """左摇杆 x/y，范围 -1.0 ~ 1.0（中心 0）。"""
        ix = self._info.dwXpos
        iy = self._info.dwYpos
        x = (ix - 32767) / 32767.0
        y = (iy - 32767) / 32767.0
        # 死区
        if abs(x) < 0.15:
            x = 0.0
        if abs(y) < 0.15:
            y = 0.0
        return (x, y)

    def button(self, n):
        """按钮 n（1 起）当前是否按下。"""
        return bool(self._info.dwButtons & _btn_mask(n))

    def buttons_held(self):
        """返回当前按下的按钮编号列表。"""
        out = []
        mask = self._info.dwButtons
        for i in range(1, 33):
            if mask & _btn_mask(i):
                out.append(i)
        return out
