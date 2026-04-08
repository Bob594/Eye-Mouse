from __future__ import annotations

import cv2
import numpy as np


class CalibrationOverlay:
    def __init__(self, config, screen_w: int, screen_h: int) -> None:
        self.config = config
        self.screen_w = screen_w
        self.screen_h = screen_h

    def render(self, calibrator):
        canvas = np.zeros((self.screen_h, self.screen_w, 3), dtype=np.uint8)
        target = calibrator.current_target()
        if target is not None:
            cv2.circle(canvas, target, 18, (0, 255, 255), -1)
            cv2.circle(canvas, target, 28, (255, 255, 255), 2)
        done, total = calibrator.progress()
        progress = calibrator.collect_progress()
        cv2.putText(canvas, f"Calibration {done}/{total}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(canvas, f"Hold steady: {progress:.0%}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)
        cv2.putText(canvas, "Look at the dot until it advances.", (20, self.screen_h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)
        return canvas
