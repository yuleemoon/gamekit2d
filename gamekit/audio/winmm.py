"""Windows winmm 多声道音频后端（ctypes，零第三方依赖）。

用标准库 ``wave`` 解码 WAV，再 ctypes 绑 ``winmm.dll`` 的
``waveOutOpen / waveOutWrite`` 直接写 PCM。多个音效同时写不同的
WAVEHDR，Windows 音频引擎自动混音——告别 winsound "一次只能放一个"。

仅 Windows。其他平台由 sound.py 走 subprocess 兜底。
"""
import ctypes
from ctypes import wintypes
import wave
import threading
import struct

winmm = ctypes.windll.winmm

# ---- 常量 ----
WAVE_FORMAT_PCM = 1
WAVE_MAPPER = -1
CALLBACK_NULL = 0
WHDR_DONE = 1
WHDR_PREPARED = 2

# 错误码（MMSYSERR_NOERROR = 0）
MMSYSERR_NOERROR = 0


class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD),
        ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD),
        ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD),
        ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD),
    ]


class WAVEHDR(ctypes.Structure):
    _fields_ = [
        ("lpData", ctypes.c_void_p),
        ("dwBufferLength", wintypes.DWORD),
        ("dwBytesRecorded", wintypes.DWORD),
        ("dwUser", ctypes.c_void_p),
        ("dwFlags", wintypes.DWORD),
        ("dwLoops", wintypes.DWORD),
        ("lpNext", ctypes.c_void_p),
        ("reserved", ctypes.c_void_p),
    ]


# ---- 类型签名 ----
HWAVEOUT = wintypes.HANDLE
winmm.waveOutOpen.argtypes = [ctypes.POINTER(HWAVEOUT),
                              wintypes.UINT, ctypes.POINTER(WAVEFORMATEX),
                              wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
winmm.waveOutOpen.restype = wintypes.UINT
winmm.waveOutPrepareHeader.argtypes = [HWAVEOUT,
                                       ctypes.POINTER(WAVEHDR), wintypes.UINT]
winmm.waveOutPrepareHeader.restype = wintypes.UINT
winmm.waveOutWrite.argtypes = [HWAVEOUT,
                               ctypes.POINTER(WAVEHDR), wintypes.UINT]
winmm.waveOutWrite.restype = wintypes.UINT
winmm.waveOutUnprepareHeader.argtypes = [HWAVEOUT,
                                         ctypes.POINTER(WAVEHDR), wintypes.UINT]
winmm.waveOutUnprepareHeader.restype = wintypes.UINT
winmm.waveOutReset.argtypes = [HWAVEOUT]
winmm.waveOutReset.restype = wintypes.UINT
winmm.waveOutClose.argtypes = [HWAVEOUT]
winmm.waveOutClose.restype = wintypes.UINT


# 全局输出设备（共享一个，多音效靠多 WAVEHDR 混音）
_hwavo = HWAVEOUT()
_lock = threading.Lock()
_format = None
_active = []   # 正在播放的 (buffer, header)，防止被 GC


def _open_device(fmt):
    """打开/重开输出设备（格式变化时）。"""
    global _hwavo, _format
    with _lock:
        if _format is not None and _format.nSamplesPerSec == fmt.nSamplesPerSec \
                and _format.nChannels == fmt.nChannels \
                and _format.wBitsPerSample == fmt.wBitsPerSample:
            return _hwavo
        if _hwavo:
            winmm.waveOutReset(_hwavo)
            winmm.waveOutClose(_hwavo)
        rc = winmm.waveOutOpen(ctypes.byref(_hwavo), WAVE_MAPPER,
                               ctypes.byref(fmt), 0, 0, CALLBACK_NULL)
        if rc != MMSYSERR_NOERROR:
            raise RuntimeError("waveOutOpen failed: %d" % rc)
        _format = fmt
        return _hwavo


def play_pcm(pcm_bytes, sample_rate=44100, channels=1, bits=16, loop=False):
    """把一段 PCM 写进输出设备播放。多段同时调，系统自动混音。"""
    fmt = WAVEFORMATEX()
    fmt.wFormatTag = WAVE_FORMAT_PCM
    fmt.nChannels = channels
    fmt.nSamplesPerSec = sample_rate
    fmt.wBitsPerSample = bits
    fmt.nBlockAlign = channels * bits // 8
    fmt.nAvgBytesPerSec = sample_rate * fmt.nBlockAlign
    fmt.cbSize = 0

    h = _open_device(fmt)
    # buffer 必须常驻内存
    buf = ctypes.create_string_buffer(pcm_bytes, len(pcm_bytes))
    hdr = WAVEHDR()
    hdr.lpData = ctypes.cast(buf, ctypes.c_void_p)
    hdr.dwBufferLength = len(pcm_bytes)
    hdr.dwFlags = 0
    hdr.dwLoops = 1

    with _lock:
        rc = winmm.waveOutPrepareHeader(h, ctypes.byref(hdr), ctypes.sizeof(hdr))
        if rc != MMSYSERR_NOERROR:
            return
        if loop:
            hdr.dwLoops = 0   # 无限循环（需要事件，这里简化：播完重写）
        rc = winmm.waveOutWrite(h, ctypes.byref(hdr), ctypes.sizeof(hdr))
        if rc == MMSYSERR_NOERROR:
            _active.append((buf, hdr))


def stop_all():
    """停止所有音效。"""
    global _active
    with _lock:
        if _hwavo:
            winmm.waveOutReset(_hwavo)
        for buf, hdr in _active:
            try:
                winmm.waveOutUnprepareHeader(_hwavo, ctypes.byref(hdr),
                                             ctypes.sizeof(hdr))
            except Exception:
                pass
        _active = []


def load_wav(path):
    """读 WAV 文件，返回 (pcm_bytes, sample_rate, channels, bits)。"""
    with wave.open(path, "rb") as w:
        ch = w.getnchannels()
        sr = w.getframerate()
        sw = w.getsampwidth()
        n = w.getnframes()
        raw = w.readframes(n)
    return raw, sr, ch, sw * 8
