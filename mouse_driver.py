from __future__ import annotations

import ctypes
from ctypes import wintypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

ULONG_PTR = ctypes.c_uint64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_uint32


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", INPUT_UNION)]


INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000


class MouseDriver:
    def __init__(self, display_manager) -> None:
        self.display_manager = display_manager
        self.left_is_down = False
        self.right_is_down = False
        self._last_move_xy: tuple[int, int] | None = None

    def _send_input(self, flags: int, dx: int = 0, dy: int = 0, mouse_data: int = 0) -> None:
        mi = MOUSEINPUT(dx, dy, mouse_data, flags, 0, ULONG_PTR(0))
        cmd = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
        ctypes.windll.user32.SendInput(1, ctypes.pointer(cmd), ctypes.sizeof(cmd))

    def move(self, x: int, y: int) -> None:
        xy = (int(x), int(y))
        if self._last_move_xy == xy:
            return
        v_left = self.display_manager.virtual_left
        v_top = self.display_manager.virtual_top
        v_w = self.display_manager.virtual_width
        v_h = self.display_manager.virtual_height
        rel_x = xy[0] - v_left
        rel_y = xy[1] - v_top
        abs_x = int((rel_x * 65535) / max(v_w - 1, 1))
        abs_y = int((rel_y * 65535) / max(v_h - 1, 1))
        self._send_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, abs_x, abs_y)
        self._last_move_xy = xy

    def left_click(self) -> None:
        self._send_input(MOUSEEVENTF_LEFTDOWN)
        self._send_input(MOUSEEVENTF_LEFTUP)

    def right_click(self) -> None:
        self._send_input(MOUSEEVENTF_RIGHTDOWN)
        self._send_input(MOUSEEVENTF_RIGHTUP)

    def left_down(self) -> None:
        if not self.left_is_down:
            self._send_input(MOUSEEVENTF_LEFTDOWN)
            self.left_is_down = True

    def left_up(self) -> None:
        if self.left_is_down:
            self._send_input(MOUSEEVENTF_LEFTUP)
            self.left_is_down = False

    def right_up(self) -> None:
        if self.right_is_down:
            self._send_input(MOUSEEVENTF_RIGHTUP)
            self.right_is_down = False

    def scroll(self, delta: int) -> None:
        self._send_input(MOUSEEVENTF_WHEEL, mouse_data=delta)

    def reset_motion_state(self) -> None:
        self._last_move_xy = None

    def emergency_release(self) -> None:
        self.left_up()
        self.right_up()

    def full_reset(self) -> None:
        self.emergency_release()
        self.reset_motion_state()
