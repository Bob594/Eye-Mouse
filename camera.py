from __future__ import annotations

import cv2


class CameraStream:
    def __init__(self, config) -> None:
        self.config = config
        self.cap = None
        self.actual_resolution = (config.frame_width, config.frame_height)

    def open(self) -> None:
        if self.cap is not None:
            return
        self.cap = cv2.VideoCapture(self.config.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError("Could not open camera.")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.config.frame_width
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.config.frame_height
        self.actual_resolution = (width, height)

    def read(self):
        if self.cap is None:
            return None
        ok, frame = self.cap.read()
        if not ok:
            return None
        if self.config.mirror_frame:
            frame = cv2.flip(frame, 1)
        return frame

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
