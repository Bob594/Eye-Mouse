from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonitorInfo:
    index: int
    left: int
    top: int
    width: int
    height: int
    is_primary: bool
    device_name: str = ""

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def layout_signature(self) -> str:
        return f"{self.device_name}:{self.left},{self.top},{self.width},{self.height}:{int(self.is_primary)}"
