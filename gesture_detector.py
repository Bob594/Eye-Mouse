from __future__ import annotations

import math
import time
from dataclasses import dataclass

from app.intent.events import GestureCandidate, GestureType
from app.tracking.landmark_utils import (
    LEFT_EYE_BOTTOM,
    LEFT_EYE_LEFT,
    LEFT_EYE_RIGHT,
    LEFT_EYE_TOP,
    RIGHT_EYE_BOTTOM,
    RIGHT_EYE_LEFT,
    RIGHT_EYE_RIGHT,
    RIGHT_EYE_TOP,
)


@dataclass
class BlinkMetrics:
    left_ear: float
    right_ear: float
    left_baseline: float
    right_baseline: float
    left_closed: bool
    right_closed: bool
    left_just_closed: bool
    right_just_closed: bool


class EyeClosureTracker:
    def __init__(self, config) -> None:
        self.config = config
        self.history: list[float] = []
        self.closed = False
        self.closed_start: float | None = None
        self.last_release_duration: float = 0.0
        self.just_closed = False

    def baseline(self) -> float:
        return sum(self.history) / len(self.history) if self.history else 0.30

    def threshold(self) -> float:
        return min(self.config.blink_ear_threshold, self.baseline() * self.config.blink_adaptive_ratio)

    def update(self, ear: float, now: float) -> bool:
        self.just_closed = False
        if ear > self.config.blink_ear_threshold:
            self.history.append(ear)
            if len(self.history) > self.config.ear_history_len:
                self.history.pop(0)
        is_closed = ear < self.threshold()
        if is_closed and not self.closed:
            self.closed_start = now
            self.last_release_duration = 0.0
            self.just_closed = True
        elif not is_closed and self.closed:
            self.last_release_duration = now - self.closed_start if self.closed_start is not None else 0.0
            self.closed_start = None
        self.closed = is_closed
        return is_closed

    def released_duration(self) -> float:
        return self.last_release_duration

    def reset_transient(self) -> None:
        self.closed = False
        self.closed_start = None
        self.last_release_duration = 0.0
        self.just_closed = False


class GestureDetector:
    def __init__(self, config) -> None:
        self.config = config
        self.left_eye = EyeClosureTracker(config)
        self.right_eye = EyeClosureTracker(config)
        self._prev_left_only = False
        self._prev_right_only = False
        self._prev_both_closed = False
        self._last_left_blink_ts = -999.0
        self._last_nod_ts = -999.0
        self._baseline_pitch: float | None = None

    def reset_transient(self) -> None:
        self.left_eye.reset_transient()
        self.right_eye.reset_transient()
        self._prev_left_only = False
        self._prev_right_only = False
        self._prev_both_closed = False
        self._last_left_blink_ts = -999.0
        self._last_nod_ts = -999.0
        self._baseline_pitch = None

    @staticmethod
    def _dist(p1, p2) -> float:
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def _ear(self, landmarks, top, bottom, left, right, w, h) -> float:
        def get_p(idx):
            lm = landmarks.landmark[idx]
            return (lm.x * w, lm.y * h)
        vertical = self._dist(get_p(top), get_p(bottom))
        horizontal = self._dist(get_p(left), get_p(right))
        return vertical / horizontal if horizontal > 1e-6 else 1.0

    def extract_metrics(self, landmarks, w: int, h: int) -> BlinkMetrics:
        now = time.perf_counter()
        left_ear = self._ear(landmarks, LEFT_EYE_TOP, LEFT_EYE_BOTTOM, LEFT_EYE_LEFT, LEFT_EYE_RIGHT, w, h)
        right_ear = self._ear(landmarks, RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM, RIGHT_EYE_LEFT, RIGHT_EYE_RIGHT, w, h)
        left_closed = self.left_eye.update(left_ear, now)
        right_closed = self.right_eye.update(right_ear, now)
        return BlinkMetrics(
            left_ear=left_ear,
            right_ear=right_ear,
            left_baseline=self.left_eye.baseline(),
            right_baseline=self.right_eye.baseline(),
            left_closed=left_closed,
            right_closed=right_closed,
            left_just_closed=self.left_eye.just_closed,
            right_just_closed=self.right_eye.just_closed,
        )

    def detect_blink_gestures(self, metrics: BlinkMetrics) -> list[GestureCandidate]:
        now = time.perf_counter()
        out: list[GestureCandidate] = []
        l_only = metrics.left_closed and not metrics.right_closed
        r_only = metrics.right_closed and not metrics.left_closed
        both = metrics.left_closed and metrics.right_closed

        if metrics.left_just_closed or metrics.right_just_closed:
            out.append(GestureCandidate(GestureType.EYE_CLOSURE_ONSET, 1.0, now, "closure onset"))

        if self._prev_left_only and not l_only:
            dur = self.left_eye.released_duration()
            ratio = metrics.right_ear / max(metrics.left_ear, 0.01)
            if self.config.blink_min_duration_s <= dur <= self.config.blink_max_duration_s and ratio >= self.config.unilateral_open_ratio_min:
                if (now - self._last_left_blink_ts) <= self.config.double_blink_gap_s:
                    out.append(GestureCandidate(GestureType.DRAG_TOGGLE, 0.95, now, f"double left ({dur:.2f}s)"))
                    self._last_left_blink_ts = -999.0
                else:
                    out.append(GestureCandidate(GestureType.LEFT_BLINK, 0.85, now, f"left unilateral ({dur:.2f}s)"))
                    self._last_left_blink_ts = now

        if self._prev_right_only and not r_only:
            dur = self.right_eye.released_duration()
            ratio = metrics.left_ear / max(metrics.right_ear, 0.01)
            if self.config.blink_min_duration_s <= dur <= self.config.blink_max_duration_s and ratio >= self.config.unilateral_open_ratio_min:
                out.append(GestureCandidate(GestureType.RIGHT_BLINK, 0.85, now, f"right unilateral ({dur:.2f}s)"))

        if self._prev_both_closed and not both:
            dur = max(self.left_eye.released_duration(), self.right_eye.released_duration())
            if dur >= self.config.pause_blink_min_duration_s:
                out.append(GestureCandidate(GestureType.BOTH_BLINK_LONG, 0.98, now, f"pause blink ({dur:.2f}s)"))
            elif self.config.bilateral_blink_min_duration_s <= dur <= self.config.scroll_toggle_blink_max_duration_s:
                out.append(GestureCandidate(GestureType.BOTH_BLINK_SHORT, 0.90, now, f"scroll toggle ({dur:.2f}s)"))

        self._prev_left_only = l_only
        self._prev_right_only = r_only
        self._prev_both_closed = both
        return out

    def detect_nod_gesture(self, pitch_deg: float | None) -> list[GestureCandidate]:
        now = time.perf_counter()
        if pitch_deg is None:
            return []
        if self._baseline_pitch is None:
            self._baseline_pitch = pitch_deg
            return []
        delta = pitch_deg - self._baseline_pitch
        self._baseline_pitch = 0.92 * self._baseline_pitch + 0.08 * pitch_deg
        if (now - self._last_nod_ts) < self.config.nod_cooldown_s:
            return []
        if abs(delta) >= self.config.nod_pitch_threshold_deg:
            self._last_nod_ts = now
            gesture = GestureType.NOD_DOWN if delta > 0 else GestureType.NOD_UP
            return [GestureCandidate(gesture, 0.80, now, f"nod delta {delta:.1f}")]
        return []
