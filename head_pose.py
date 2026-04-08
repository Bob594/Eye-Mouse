from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.tracking.landmark_utils import FACE_MODEL_INDICES


@dataclass
class HeadPoseResult:
    pitch_deg: float
    yaw_deg: float
    roll_deg: float


class HeadPoseAdapter:
    def __init__(self, frame_w: int, frame_h: int) -> None:
        self.model_points = np.array(
            [
                (0.0, 0.0, 0.0),
                (0.0, -330.0, -65.0),
                (-225.0, 170.0, -135.0),
                (225.0, 170.0, -135.0),
                (-150.0, -150.0, -125.0),
                (150.0, -150.0, -125.0),
            ],
            dtype=np.float64,
        )
        focal_length = float(frame_w)
        center = (frame_w / 2.0, frame_h / 2.0)
        self.camera_matrix = np.array(
            [[focal_length, 0.0, center[0]], [0.0, focal_length, center[1]], [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )
        self.dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    def estimate(self, landmarks, w: int, h: int) -> HeadPoseResult | None:
        try:
            image_points = np.array(
                [(landmarks.landmark[i].x * w, landmarks.landmark[i].y * h) for i in FACE_MODEL_INDICES],
                dtype=np.float64,
            )
            ok, rotation_vector, translation_vector = cv2.solvePnP(
                self.model_points,
                image_points,
                self.camera_matrix,
                self.dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
            if not ok:
                return None
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            projection_matrix = np.hstack((rotation_matrix, translation_vector))
            _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(projection_matrix)
            return HeadPoseResult(
                pitch_deg=float(euler_angles[0, 0]),
                yaw_deg=float(euler_angles[1, 0]),
                roll_deg=float(euler_angles[2, 0]),
            )
        except Exception:
            return None
