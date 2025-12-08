"""Transforms gaze points into scanpath representation."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from statistics import mean
from typing import Iterable, List

from backend.app.video_pipeline.gaze_extractor import GazePoint


@dataclass
class ScanpathPoint:
    timestamp: float
    x: float
    y: float
    velocity: float
    confidence: float


@dataclass
class Scanpath:
    points: List[ScanpathPoint]
    sampling_rate: float
    duration: float

    def to_dict(self) -> dict:
        return {
            "sampling_rate": self.sampling_rate,
            "duration": self.duration,
            "points": [asdict(point) for point in self.points],
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2)


def _compute_velocity(previous: ScanpathPoint | None, current: tuple[float, float], dt: float) -> float:
    if previous is None or dt == 0:
        return 0.0
    dx = current[0] - previous.x
    dy = current[1] - previous.y
    return (dx**2 + dy**2) ** 0.5 / dt


def build_scanpath(gaze_points: Iterable[GazePoint], fps: float = 15.0) -> Scanpath:
    """Convert gaze stream into evenly sampled scanpath."""

    gaze_list = list(gaze_points)
    if not gaze_list:
        raise ValueError("No gaze points provided")

    sampling_interval = 1 / fps
    normalized_points: list[ScanpathPoint] = []
    previous_point: ScanpathPoint | None = None

    for gaze in gaze_list[:: max(int(len(gaze_list) / (fps * 10)), 1)]:
        velocity = _compute_velocity(previous_point, (gaze.x, gaze.y), sampling_interval)
        point = ScanpathPoint(
            timestamp=gaze.timestamp,
            x=gaze.x,
            y=gaze.y,
            velocity=velocity,
            confidence=gaze.confidence,
        )
        normalized_points.append(point)
        previous_point = point

    duration = normalized_points[-1].timestamp - normalized_points[0].timestamp
    return Scanpath(points=normalized_points, sampling_rate=fps, duration=duration)


__all__ = ["Scanpath", "ScanpathPoint", "build_scanpath"]
