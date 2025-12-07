import argparse
import json
import logging
from typing import Sequence

import grpc

from protos import model_pb2, model_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple gRPC client for the ML service")
    parser.add_argument("--host", default="localhost", help="Server hostname (default: localhost)")
    parser.add_argument("--port", type=int, default=50051, help="Server port (default: 50051)")
    parser.add_argument(
        "--features",
        type=float,
        nargs="+",
        default=[0.5, 1.0, -0.2],
        help="Feature vector for prediction (default: 0.5 1.0 -0.2)",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Call Health endpoint instead of Predict",
    )
    return parser.parse_args()


def call_health(stub: model_pb2_grpc.PredictionServiceStub) -> dict:
    response = stub.Health(model_pb2.HealthRequest())
    return {"status": response.status, "modelVersion": response.model_version}


def call_predict(
    stub: model_pb2_grpc.PredictionServiceStub, features: Sequence[float]
) -> dict:
    response = stub.Predict(model_pb2.PredictRequest(features=features))
    return {
        "prediction": response.prediction,
        "confidence": round(response.confidence, 4),
        "modelVersion": response.model_version,
    }


def main() -> None:
    args = parse_args()
    target = f"{args.host}:{args.port}"
    channel = grpc.insecure_channel(target)
    stub = model_pb2_grpc.PredictionServiceStub(channel)
    try:
        payload = call_health(stub) if args.health else call_predict(stub, args.features)
    except grpc.RpcError as exc:  # pragma: no cover - user feedback
        LOGGER.error("Request failed: %s", exc.details())
        return
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
