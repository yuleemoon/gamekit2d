# gamekit.render
# 自研渲染层：参照 pygame 的 "Surface + blit 立即模式" 思路实现。
#
# 两个部分：
#   1) 渲染内核  Surface / Window —— 自研 GDI 位块传送渲染（高性能，Windows）
#   2) 后端接口  Renderer / TkRenderer / GdiRenderer —— Game 使用的统一抽象
#
# 全程零第三方依赖（ctypes 直接调系统 GDI / user32）。

from .backend import Renderer, TkRenderer, GdiRenderer
from .surface import Surface
from .window import Window

__all__ = ["Renderer", "TkRenderer", "GdiRenderer", "Surface", "Window"]
