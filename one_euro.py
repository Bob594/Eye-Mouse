from __future__ import annotations

import math
import time


class LowPassFilter:
    def __init__(self, alpha: float, init_value: float = 0.0) -> None:
        self.alpha = alpha
        self.s = init_value
        self.initialized = False

    def filter(self, value: float, alpha: float | None = None) -> float:
        if alpha is not None:
            self.alpha = alpha
        if not self.initialized:
            self.s = value
            self.initialized = True
            return value
        self.s = self.alpha * value + (1.0 - self.alpha) * self.s
        return self.s

    def reset(self) -> None:
        self.initialized = False


class OneEuroFilter:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.02, d_cutoff: float = 1.0) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_filter = LowPassFilter(alpha=1.0)
        self.dx_filter = LowPassFilter(alpha=1.0)
        self.last_time: float | None = None
        self.last_x: float | None = None

    def _alpha(self, dt: float, cutoff: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: float, timestamp: float | None = None) -> float:
        t = time.perf_counter() if timestamp is None else timestamp
        if self.last_time is None or self.last_x is None:
            self.last_time = t
            self.last_x = x
            return self.x_filter.filter(x, alpha=1.0)

        dt = max(t - self.last_time, 1e-6)
        dx = (x - self.last_x) / dt
        edx = self.dx_filter.filter(dx, alpha=self._alpha(dt, self.d_cutoff))
        cutoff = self.min_cutoff + self.beta * abs(edx)
        result = self.x_filter.filter(x, alpha=self._alpha(dt, cutoff))
        self.last_time = t
        self.last_x = x
        return result

    def reset(self, value: float | None = None, timestamp: float | None = None) -> None:
        self.x_filter.reset()
        self.dx_filter.reset()
        self.last_time = timestamp
        self.last_x = value
