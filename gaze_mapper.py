from __future__ import annotations

import math
import time
import numpy as np

from app.config import AppConfig
from app.filtering.one_euro import OneEuroFilter


class GazeMapper:
    def __init__(self, config: AppConfig, screen_w: int, screen_h: int) -> None:
        self.config = config
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._transform: np.ndarray | None = None
        self._smoothed_x = screen_w / 2.0
        self._smoothed_y = screen_h / 2.0
        self._prev_tracker_pt: tuple[float, float] | None = None
        self._freeze_until = 0.0
        self._frozen_xy: tuple[float, float] | None = None
        self._was_frozen_last_frame = False
        self._filter_x = OneEuroFilter(config.one_euro_min_cutoff, config.one_euro_beta, config.one_euro_d_cutoff)
        self._filter_y = OneEuroFilter(config.one_euro_min_cutoff, config.one_euro_beta, config.one_euro_d_cutoff)

    def set_calibration(self, matrix: np.ndarray | None) -> None:
        self._transform = matrix

    def is_calibrated(self) -> bool:
        return self._transform is not None

    def is_frozen(self, now: float | None = None) -> bool:
        now = time.perf_counter() if now is None else now
        return now < self._freeze_until

    def freeze(self, now: float) -> None:
        self._freeze_until = max(self._freeze_until, now + self.config.cursor_freeze_on_blink_s)
        self._frozen_xy = (self._smoothed_x, self._smoothed_y)

    def reanchor_to_tracker(self, tracker_px: tuple[float, float]) -> None:
        self._prev_tracker_pt = tracker_px
        if self._transform is None:
            self._smoothed_x = self.screen_w / 2.0
            self._smoothed_y = self.screen_h / 2.0
            self._reset_filters_to_output()
            return
        raw_x, raw_y = self._map_tracker_to_screen(tracker_px)
        self._smoothed_x = raw_x
        self._smoothed_y = raw_y
        self._reset_filters_to_output()

    def reset_tracker_memory(self) -> None:
        self._prev_tracker_pt = None
        self._freeze_until = 0.0
        self._frozen_xy = None
        self._was_frozen_last_frame = False
        self._reset_filters_to_output()

    def reset_all(self) -> None:
        self._prev_tracker_pt = None
        self._smoothed_x = self.screen_w / 2.0
        self._smoothed_y = self.screen_h / 2.0
        self._freeze_until = 0.0
        self._frozen_xy = None
        self._was_frozen_last_frame = False
        self._reset_filters_to_output()

    def resize_monitor_space(self, screen_w: int, screen_h: int) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._smoothed_x = min(max(self._smoothed_x, 0.0), float(screen_w - 1))
        self._smoothed_y = min(max(self._smoothed_y, 0.0), float(screen_h - 1))
        self._reset_filters_to_output()

    def update(self, tracker_px: tuple[float, float]) -> tuple[int, int]:
        now = time.perf_counter()
        tx, ty = tracker_px
        if self._prev_tracker_pt is not None:
            px, py = self._prev_tracker_pt
            if math.hypot(tx - px, ty - py) < self.config.dead_zone_px:
                tx, ty = px, py
        self._prev_tracker_pt = (tx, ty)
        if self._transform is None:
            return self._clamp_xy(self._smoothed_x, self._smoothed_y)
        raw_x, raw_y = self._map_tracker_to_screen((tx, ty))
        if self.is_frozen(now):
            self._was_frozen_last_frame = True
            return self._clamp_xy(*(self._frozen_xy or (self._smoothed_x, self._smoothed_y)))
        if self._was_frozen_last_frame:
            self._filter_x.reset(value=raw_x, timestamp=now)
            self._filter_y.reset(value=raw_y, timestamp=now)
            self._smoothed_x = raw_x
            self._smoothed_y = raw_y
            self._was_frozen_last_frame = False
            return self._clamp_smoothed()
        self._smoothed_x = self._filter_x.filter(raw_x, timestamp=now)
        self._smoothed_y = self._filter_y.filter(raw_y, timestamp=now)
        return self._clamp_smoothed()

    def _reset_filters_to_output(self) -> None:
        now = time.perf_counter()
        self._filter_x.reset(value=self._smoothed_x, timestamp=now)
        self._filter_y.reset(value=self._smoothed_y, timestamp=now)

    def _map_tracker_to_screen(self, tracker_px: tuple[float, float]) -> tuple[float, float]:
        tx, ty = tracker_px
        vec = np.array([tx, ty, 1.0], dtype=np.float64)
        mapped = self._transform @ vec
        return float(mapped[0]), float(mapped[1])

    def _clamp_xy(self, x: float, y: float) -> tuple[int, int]:
        margin = self.config.screen_margin_px
        cx = int(np.clip(x, margin, self.screen_w - 1 - margin))
        cy = int(np.clip(y, margin, self.screen_h - 1 - margin))
        return cx, cy

    def _clamp_smoothed(self) -> tuple[int, int]:
        return self._clamp_xy(self._smoothed_x, self._smoothed_y)
