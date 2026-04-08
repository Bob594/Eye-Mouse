from __future__ import annotations

import ctypes
from ctypes import wintypes

from app.display.monitor_info import MonitorInfo

MONITORINFOF_PRIMARY = 0x00000001
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


MonitorEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)


class DisplayManager:
    def __init__(self) -> None:
        self.user32 = ctypes.windll.user32
        self.monitors: list[MonitorInfo] = self._enumerate_monitors()
        if not self.monitors:
            raise RuntimeError("No monitors found.")
        self.active_monitor_index = next((i for i, m in enumerate(self.monitors) if m.is_primary), 0)

    @property
    def active_monitor(self) -> MonitorInfo:
        if not self.monitors:
            raise RuntimeError("No active monitor available.")
        if not (0 <= self.active_monitor_index < len(self.monitors)):
            self.active_monitor_index = 0
        return self.monitors[self.active_monitor_index]

    @property
    def virtual_left(self) -> int:
        return int(self.user32.GetSystemMetrics(SM_XVIRTUALSCREEN))

    @property
    def virtual_top(self) -> int:
        return int(self.user32.GetSystemMetrics(SM_YVIRTUALSCREEN))

    @property
    def virtual_width(self) -> int:
        return int(self.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))

    @property
    def virtual_height(self) -> int:
        return int(self.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))

    def refresh(self) -> None:
        old_name = self.active_monitor.device_name if self.monitors else ""
        self.monitors = self._enumerate_monitors()
        if not self.monitors:
            raise RuntimeError("No monitors found after refresh.")
        found = False
        for i, mon in enumerate(self.monitors):
            if mon.device_name == old_name:
                self.active_monitor_index = i
                found = True
                break
        if not found:
            self.active_monitor_index = next((i for i, m in enumerate(self.monitors) if m.is_primary), 0)

    def next_monitor(self) -> MonitorInfo:
        self.refresh()
        self.active_monitor_index = (self.active_monitor_index + 1) % len(self.monitors)
        return self.active_monitor

    def previous_monitor(self) -> MonitorInfo:
        self.refresh()
        self.active_monitor_index = (self.active_monitor_index - 1) % len(self.monitors)
        return self.active_monitor

    def clamp_to_active_monitor(self, x: float, y: float) -> tuple[int, int]:
        mon = self.active_monitor
        cx = min(max(int(round(x)), mon.left), mon.right - 1)
        cy = min(max(int(round(y)), mon.top), mon.bottom - 1)
        return cx, cy

    def local_to_virtual(self, x_local: float, y_local: float) -> tuple[int, int]:
        mon = self.active_monitor
        x = mon.left + int(round(x_local))
        y = mon.top + int(round(y_local))
        return self.clamp_to_active_monitor(x, y)

    def get_active_monitor_size(self) -> tuple[int, int]:
        mon = self.active_monitor
        return mon.width, mon.height

    def _enumerate_monitors(self) -> list[MonitorInfo]:
        monitors: list[MonitorInfo] = []

        def callback(hmonitor, hdc, lprect, lparam):
            info = MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(MONITORINFOEXW)
            ok = self.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info))
            if ok:
                left = int(info.rcMonitor.left)
                top = int(info.rcMonitor.top)
                right = int(info.rcMonitor.right)
                bottom = int(info.rcMonitor.bottom)
                monitors.append(MonitorInfo(len(monitors), left, top, right - left, bottom - top, bool(info.dwFlags & MONITORINFOF_PRIMARY), str(info.szDevice)))
            return True

        self.user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(callback), 0)
        monitors.sort(key=lambda m: (not m.is_primary, m.left, m.top, m.index))
        return [MonitorInfo(i, m.left, m.top, m.width, m.height, m.is_primary, m.device_name) for i, m in enumerate(monitors)]
