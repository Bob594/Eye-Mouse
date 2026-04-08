from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import numpy as np

from app.config import AppConfig


class CalibrationState(Enum):
    WAITING = auto()
    COLLECTING = auto()
    DONE = auto()


@dataclass
class CalibrationData:
    transform_matrix: np.ndarray
    tracker_points: np.ndarray
    screen_points: np.ndarray
    monitor_signature: str


class Calibration:
    def __init__(self, config: AppConfig, screen_w: int, screen_h: int) -> None:
        self.config = config
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._monitor_signature = "unknown"
        self._data: CalibrationData | None = None
        self.set_screen_size(screen_w, screen_h)
        self.start()

    def set_screen_size(self, screen_w: int, screen_h: int) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._targets = [(int(tx * screen_w), int(ty * screen_h)) for tx, ty in self.config.calibration_targets]

    def start(self, monitor_signature: str = "unknown") -> None:
        self._monitor_signature = monitor_signature
        self._state = CalibrationState.WAITING
        self._current_idx = 0
        self._settle_counter = 0
        self._collect_counter = 0
        self._tracker_samples: list[list[float]] = []
        self._screen_targets_used: list[tuple[int, int]] = []
        self._current_samples: list[tuple[float, float]] = []
        self._data = None

    def update(self, tracker_px: tuple[float, float] | None) -> None:
        if self._state == CalibrationState.DONE or tracker_px is None:
            return
        if self._state == CalibrationState.WAITING:
            self._settle_counter += 1
            if self._settle_counter >= self.config.calibration_settle_frames:
                self._state = CalibrationState.COLLECTING
                self._collect_counter = 0
                self._current_samples = []
            return
        self._current_samples.append(tracker_px)
        self._collect_counter += 1
        if self._collect_counter >= self.config.calibration_frames:
            samples = np.array(self._current_samples, dtype=np.float64)
            mean = np.mean(samples, axis=0)
            std = np.std(samples, axis=0)
            spread = float(np.linalg.norm(std))
            if spread <= self.config.max_point_std_px:
                self._tracker_samples.append(mean.tolist())
                self._screen_targets_used.append(self._targets[self._current_idx])
                self._current_idx += 1
            self._settle_counter = 0
            self._collect_counter = 0
            self._current_samples = []
            if self._current_idx >= len(self._targets):
                self._fit()
                self._state = CalibrationState.DONE
            else:
                self._state = CalibrationState.WAITING

    def is_done(self) -> bool:
        return self._state == CalibrationState.DONE

    def current_target(self) -> tuple[int, int] | None:
        if self._current_idx >= len(self._targets):
            return None
        return self._targets[self._current_idx]

    def progress(self) -> tuple[int, int]:
        return self._current_idx, len(self._targets)

    def collect_progress(self) -> float:
        if self._state != CalibrationState.COLLECTING:
            return 0.0
        return min(self._collect_counter / self.config.calibration_frames, 1.0)

    def get_data(self) -> CalibrationData | None:
        return self._data

    def save(self) -> None:
        if self._data is None:
            return
        path = self.config.calibration_path
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path,
            transform_matrix=self._data.transform_matrix,
            tracker_points=self._data.tracker_points,
            screen_points=self._data.screen_points,
            monitor_signature=self._data.monitor_signature,
        )

    def load(self, expected_monitor_signature: str | None = None) -> bool:
        path = self.config.calibration_path
        if not path.exists():
            return False
        try:
            npz = np.load(path, allow_pickle=True)
            saved_sig = str(npz["monitor_signature"]) if "monitor_signature" in npz else "unknown"
            if expected_monitor_signature is not None and saved_sig != expected_monitor_signature:
                return False
            self._data = CalibrationData(npz["transform_matrix"], npz["tracker_points"], npz["screen_points"], saved_sig)
            self._state = CalibrationState.DONE
            return True
        except Exception:
            return False

    def _fit(self) -> None:
        src = np.array(self._tracker_samples, dtype=np.float64)
        dst = np.array(self._screen_targets_used, dtype=np.float64)
        ones = np.ones((len(src), 1), dtype=np.float64)
        A = np.hstack([src, ones])
        M, _, _, _ = np.linalg.lstsq(A, dst, rcond=None)
        transform = M.T
        self._data = CalibrationData(transform, src, dst, self._monitor_signature)
