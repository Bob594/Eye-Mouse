from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from app.intent.events import AppState, InteractionMode


@dataclass
class CursorSample:
    x: int
    y: int
    timestamp: float
    frozen: bool


@dataclass
class SessionState:
    app_state: AppState = AppState.CALIBRATING
    interaction_mode: InteractionMode = InteractionMode.POINTER
    last_click_ts: float = 0.0
    last_drag_toggle_ts: float = 0.0
    last_scroll_ts: float = 0.0
    last_scroll_mode_activity_ts: float = 0.0
    drag_active: bool = False
    cursor_history: deque = field(default_factory=lambda: deque(maxlen=32))
    last_intent_reason: str = ""
    last_reject_reason: str = ""

    def note_cursor(self, cursor_xy: tuple[int, int] | None, frozen: bool) -> None:
        if cursor_xy is None:
            return
        self.cursor_history.append(CursorSample(int(cursor_xy[0]), int(cursor_xy[1]), time.perf_counter(), frozen))

    def clear_cursor_history(self) -> None:
        self.cursor_history.clear()

    def now(self) -> float:
        return time.perf_counter()
