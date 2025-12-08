"""Interface to the trained autism risk model."""
from __future__ import annotations

import importlib
from typing import Any, Callable, Dict

from backend.app.video_pipeline.scanpath_builder import Scanpath


class ModelRunner:
    """Thin wrapper around the provided Python model file."""

    def __init__(self, module_name: str) -> None:
        module = importlib.import_module(module_name)
        if not hasattr(module, "predict_risk"):
            raise AttributeError(
                f"Module {module_name} must expose a `predict_risk(scanpath)` function"
            )
        self._predict_fn: Callable[[Scanpath], Dict[str, Any]] = getattr(module, "predict_risk")

    def predict(self, scanpath: Scanpath) -> Dict[str, Any]:
        return self._predict_fn(scanpath)


__all__ = ["ModelRunner"]
