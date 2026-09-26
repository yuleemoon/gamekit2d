"""按键常量与标准化。

使用方式：:

    from gamekit import Key

    @game.on_key(Key.SPACE)   # 空格键
    def jump(): ...

    @game.on_key("a")         # A 键（大小写均可）
    def left(): ...

按键名称最终会被 ``normalize`` 统一为 tkinter 的 keysym 字符串。
"""


class _Keys:
    """按键常量容器。``Key.SPACE`` / ``Key.UP`` / ``Key.A`` 等。"""

    # ---- 方向与常用键 ----
    SPACE = "space"
    UP = "Up"
    DOWN = "Down"
    LEFT = "Left"
    RIGHT = "Right"
    ENTER = "Return"
    RETURN = "Return"
    ESC = "Escape"
    ESCAPE = "Escape"
    TAB = "Tab"
    BACKSPACE = "BackSpace"
    DELETE = "Delete"
    HOME = "Home"
    END = "End"
    PAGE_UP = "Prior"
    PAGE_DOWN = "Next"
    CAPS_LOCK = "Caps_Lock"

    # ---- 修饰键（按住即可，通常配合组合使用）----
    SHIFT = "Shift_L"
    CTRL = "Control_L"
    CONTROL = "Control_L"
    ALT = "Alt_L"

    # ---- 功能键 ----
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    F5 = "F5"
    F6 = "F6"
    F7 = "F7"
    F8 = "F8"
    F9 = "F9"
    F10 = "F10"
    F11 = "F11"
    F12 = "F12"

    def __getattr__(self, name):
        # 动态支持 Key.A ~ Key.Z（字母）与 Key.D0 ~ Key.D9 之外的单个数字写法
        if len(name) == 1 and name.isalpha():
            return name.lower()
        if len(name) == 1 and name.isdigit():
            return name
        raise AttributeError("不存在的按键常量: Key.%s" % name)


# 单例：`Key` 是模块级唯一实例，而不是类
Key = _Keys()


# 别名映射：把用户各种写法统一到 tkinter keysym
_ALIASES = {
    "space": "space",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "enter": "Return",
    "return": "Return",
    "esc": "Escape",
    "escape": "Escape",
    "shift": "Shift_L",
    "ctrl": "Control_L",
    "control": "Control_L",
    "alt": "Alt_L",
    "tab": "Tab",
    "backspace": "BackSpace",
    "delete": "Delete",
    "capslock": "Caps_Lock",
    "caps_lock": "Caps_Lock",
    "home": "Home",
    "end": "End",
    "pageup": "Prior",
    "pagedown": "Next",
    "paused": "Pause",
    "printscreen": "Print",
    "insert": "Insert",
}


def normalize(key):
    """把任意按键写法标准化为 tkinter keysym 字符串。

    支持：``"space"`` / ``"SPACE"`` / ``Key.SPACE`` / ``"a"`` / ``"A"`` / ``"F5"``
    """
    if key is None:
        return None
    if not isinstance(key, str):
        raise TypeError("按键必须是字符串，例如 'space'、'a'、Key.SPACE，收到: %r" % (key,))
    lower = key.lower()
    if lower in _ALIASES:
        return _ALIASES[lower]
    if len(key) == 1:
        if key.isalpha():
            return key.lower()
        if key.isdigit():
            return key
    if len(key) == 2 and key[0] in "fF" and key[1].isdigit():
        return key.upper()
    # 未知按键原样返回，交给 tkinter 处理
    return key
