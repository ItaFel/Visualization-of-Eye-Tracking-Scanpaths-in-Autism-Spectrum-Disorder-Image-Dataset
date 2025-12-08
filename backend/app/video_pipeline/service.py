"""High-level orchestrator for video → scanpath → inference pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from backend.app.config import get_settings
from backend.app.video_pipeline.gaze_extractor import extract_gaze_points
from backend.app.video_pipeline.model_runner import ModelRunner
from backend.app.video_pipeline.scanpath_builder import Scanpath, build_scanpath


class VideoProcessingService:
    """Runs the full preprocessing and inference pipeline."""

    def __init__(self, model_runner: ModelRunner | None = None) -> None:
        self.settings = get_settings()
        self.model_runner = model_runner or ModelRunner(self.settings.model_module)

    def _persist_scanpath(self, session_id: int, scanpath: Scanpath) -> Path:
        output_path = (
            Path(self.settings.results_dir) / f"session_{session_id:04d}_scanpath.json"
        )
        output_path.write_text(scanpath.to_json(), encoding="utf-8")
        return output_path

    def process_video(self, session_id: int, video_path: str | Path) -> Dict[str, Any]:
        gaze_points = extract_gaze_points(video_path)
        scanpath = build_scanpath(gaze_points)
        scanpath_path = self._persist_scanpath(session_id, scanpath)
        model_result = self.model_runner.predict(scanpath)
        model_result["scanpath_path"] = str(scanpath_path)
        return model_result


__all__ = ["VideoProcessingService"]
