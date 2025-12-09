"""Low-level utilities for extracting gaze points from raw video."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import cv2
import mediapipe as mp


@dataclass
class GazePoint:
    """Normalized gaze coordinate sampled from the video."""

    timestamp: float
    x: float
    y: float
    confidence: float


_LEFT_EYE_LANDMARKS = [33, 133, 159, 145]
_RIGHT_EYE_LANDMARKS = [362, 263, 386, 374]


def _average_eye_center(landmarks, indices) -> tuple[float, float]:
    xs = [landmarks[i].x for i in indices]
    ys = [landmarks[i].y for i in indices]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def extract_gaze_points(video_path: str | Path, frame_stride: int = 2) -> List[GazePoint]:
    """Extract normalized gaze positions using MediaPipe FaceMesh.

    The function is intentionally conservative so it can run on-device.
    """

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(path)

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():  # pragma: no cover - depends on OpenCV backend
        raise RuntimeError(f"Unable to open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    gaze_points: list[GazePoint] = []
    frame_index = 0

    try:
        while True:
            success, frame = capture.read()
            if not success:
                break

            if frame_index % frame_stride != 0:
                frame_index += 1
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)
            if not results.multi_face_landmarks:
                frame_index += 1
                continue

            face_landmarks = results.multi_face_landmarks[0].landmark
            left_x, left_y = _average_eye_center(face_landmarks, _LEFT_EYE_LANDMARKS)
            right_x, right_y = _average_eye_center(face_landmarks, _RIGHT_EYE_LANDMARKS)
            avg_x = (left_x + right_x) / 2
            avg_y = (left_y + right_y) / 2

            timestamp = frame_index / fps
            gaze_points.append(
                GazePoint(timestamp=timestamp, x=avg_x, y=avg_y, confidence=0.9)
            )
            frame_index += 1
    finally:
        capture.release()
        face_mesh.close()

    return gaze_points


__all__ = ["GazePoint", "extract_gaze_points"]
