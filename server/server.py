import logging
import math
import os
import pickle
from concurrent import futures
from pathlib import Path
from typing import List, Tuple

import grpc

from protos import model_pb2, model_pb2_grpc


_LOGGER = logging.getLogger(__name__)


class SimpleLogisticModel:
    """Lightweight logistic regression-style model stored as pickle."""

    def __init__(self, weights: List[float], bias: float, label_map: dict[int, str]):
        self._weights = weights
        self._bias = bias
        self._label_map = label_map

    def predict(self, features: List[float]) -> Tuple[str, float]:
        if len(features) != len(self._weights):
            raise ValueError(
                f"Model expects {len(self._weights)} features, got {len(features)}"
            )
        logit = sum(w * x for w, x in zip(self._weights, features)) + self._bias
        prob = 1.0 / (1.0 + math.exp(-logit))
        label_idx = 1 if prob >= 0.5 else 0
        label = self._label_map.get(label_idx, str(label_idx))
        confidence = prob if label_idx == 1 else 1.0 - prob
        return label, confidence


class PredictionService(model_pb2_grpc.PredictionServiceServicer):
    def __init__(self, model: SimpleLogisticModel, model_version: str):
        self._model = model
        self._model_version = model_version

    def Health(self, request: model_pb2.HealthRequest, context: grpc.ServicerContext):
        return model_pb2.HealthResponse(status="ok", model_version=self._model_version)

    def Predict(self, request: model_pb2.PredictRequest, context: grpc.ServicerContext):
        features = list(request.features)
        if not features:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "`features` must not be empty")
        try:
            prediction, confidence = self._model.predict(features)
        except ValueError as exc:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        except Exception as exc:  # pragma: no cover - unexpected errors bubbled
            _LOGGER.exception("Prediction failed")
            context.abort(grpc.StatusCode.INTERNAL, f"prediction failed: {exc}")
        return model_pb2.PredictResponse(
            prediction=str(prediction), confidence=confidence, model_version=self._model_version
        )


def load_model(model_path: str | Path) -> SimpleLogisticModel:
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    with path.open("rb") as f:
        payload = pickle.load(f)
    try:
        return SimpleLogisticModel(
            weights=list(payload["weights"]),
            bias=float(payload["bias"]),
            label_map={int(k): str(v) for k, v in payload["label_map"].items()},
        )
    except KeyError as exc:
        raise ValueError(f"Model file missing key: {exc}") from exc


def serve() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    base_dir = Path(__file__).resolve().parents[1]
    default_model_path = base_dir / "models" / "model.pkl"
    model_path = os.environ.get("MODEL_PATH", str(default_model_path))
    model_version = os.environ.get("MODEL_VERSION", "v1.0.0")
    port = int(os.environ.get("PORT", "50051"))

    _LOGGER.info("Loading model from %s", model_path)
    model = load_model(model_path)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    model_pb2_grpc.add_PredictionServiceServicer_to_server(
        PredictionService(model=model, model_version=model_version), server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    _LOGGER.info("gRPC server started on port %s", port)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        _LOGGER.info("Shutting down server")
        server.stop(grace=None)


if __name__ == "__main__":
    serve()
