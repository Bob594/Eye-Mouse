from __future__ import annotations

from dataclasses import dataclass

import cv2
import mediapipe as mp

from app.tracking.head_pose import HeadPoseAdapter
from app.tracking.landmark_utils import LEFT_IRIS_INDEX, RIGHT_IRIS_INDEX


@dataclass
class TrackResult:
    face_detected: bool
    landmarks: object | None
    left_iris_px: tuple[float, float] | None
    right_iris_px: tuple[float, float] | None
    head_pose: object | None


class FaceTracker:
    def __init__(self, frame_w: int, frame_h: int, config) -> None:
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.config = config
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.pose_adapter = HeadPoseAdapter(frame_w, frame_h)

    def process(self, frame) -> TrackResult:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.mesh.process(rgb)
        if not result.multi_face_landmarks:
            return TrackResult(False, None, None, None, None)

        landmarks = result.multi_face_landmarks[0]
        left = landmarks.landmark[LEFT_IRIS_INDEX]
        right = landmarks.landmark[RIGHT_IRIS_INDEX]
        left_px = (left.x * self.frame_w, left.y * self.frame_h)
        right_px = (right.x * self.frame_w, right.y * self.frame_h)
        pose = self.pose_adapter.estimate(landmarks, self.frame_w, self.frame_h)
        return TrackResult(True, landmarks, left_px, right_px, pose)
