"""Direct2D v11: 正确 IID！"""
import ctypes

_ole32 = ctypes.windll.ole32
_ole32.CoInitializeEx(None, 0x2)

_d2d1 = ctypes.windll.LoadLibrary("d2d1.dll")
_d2d1.D2D1CreateFactory.restype = ctypes.c_long

# 正确 IID_ID2D1Factory bytes (from C program):
# 47 22 15 06 50 6f 5a 46 92 45 11 8b fd 3b 60 07
iid = (ctypes.c_byte * 16)(
    0x47, 0x22, 0x15, 0x06,
    0x50, 0x6f,
    0x5a, 0x46,
    0x92, 0x45, 0x11, 0x8b, 0xfd, 0x3b, 0x60, 0x07)

class OPTIONS(ctypes.Structure):
    _fields_ = [("debugLevel", ctypes.c_int)]
opts = OPTIONS(0)
factory = ctypes.c_void_p()

# (factoryType, riid, pOptions, ppFactory)
hr = _d2d1.D2D1CreateFactory(
    0,
    ctypes.byref(iid),
    ctypes.byref(opts),
    ctypes.byref(factory)
)
print("hr=0x%08x factory=%s" % (hr & 0xFFFFFFFF, factory.value))
