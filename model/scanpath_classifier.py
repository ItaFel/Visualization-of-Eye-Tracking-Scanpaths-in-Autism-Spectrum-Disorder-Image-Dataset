"""Placeholder model interface wrapping the research model."""
from __future__ import annotations

from statistics import mean

from backend.app.video_pipeline.scanpath_builder import Scanpath


def _estimate_dispersion(scanpath: Scanpath) -> float:
    xs = [point.x for point in scanpath.points]
    ys = [point.y for point in scanpath.points]
    if not xs or not ys:
        return 0.0
    return (max(xs) - min(xs) + max(ys) - min(ys)) / 2


def predict_risk(scanpath: Scanpath) -> dict:
    """Simplistic placeholder for the real ML model.

    Replace this implementation with the research-grade model. It receives a
    ``Scanpath`` object and must return a dictionary with ``risk_score``,
    ``risk_level`` and ``recommendations`` keys.
    """

    dispersion = _estimate_dispersion(scanpath)
    avg_velocity = mean(point.velocity for point in scanpath.points)

    risk_score = min(1.0, dispersion * 0.8 + avg_velocity * 0.5)
    risk_level = "high" if risk_score > 0.6 else "low"
    recommendations = (
        "Consult a specialist for further evaluation"
        if risk_level == "high"
        else "Continue regular monitoring"
    )

    return {
        "risk_score": float(risk_score),
        "risk_level": risk_level,
        "recommendations": recommendations,
    }
