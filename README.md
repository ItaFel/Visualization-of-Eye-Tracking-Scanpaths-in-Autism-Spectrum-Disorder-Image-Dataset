# ml_grpc_service

Минимальный пример gRPC-сервиса для обёртки простой ML-модели (логистическая регрессия с заранее сохранёнными весами). Сервис реализует методы `Health` и `Predict`, возвращающие статус модели и предсказание вместе с вероятностью.

## Структура проекта

```
ml_grpc_service/
├── client/
│   └── client.py
├── models/
│   └── model.pkl
├── protos/
│   └── model.proto
├── server/
│   └── server.py
├── requirements.txt
├── Dockerfile
└── README.md
```

Сгенерированные файлы `protos/model_pb2*.py` уже находятся в репозитории, поэтому этап генерации потребуется только при изменении `model.proto`.

## Локальный запуск (без Docker)

1. Установите зависимости:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. (Опционально) пересоберите gRPC-stubs после изменения `model.proto`:
   ```bash
   python -m grpc_tools.protoc -I protos --python_out=. --grpc_python_out=. protos/model.proto
   ```
3. Запустите сервер:
   ```bash
   export MODEL_PATH=$(pwd)/models/model.pkl
   export MODEL_VERSION=v1.0.0
   python -m server.server
   ```
4. В другом терминале вызовите /predict через клиента:
   ```bash
   python -m client.client --features 0.2 1.1 -0.4
   # {"prediction": "1", "confidence": 0.8732, "modelVersion": "v1.0.0"}
   ```
5. Проверить /health можно через того же клиента:
   ```bash
   python -m client.client --health
   # {"status": "ok", "modelVersion": "v1.0.0"}
   ```

## Docker

### Сборка образа
```bash
docker build -t grpc-ml-service .
```

### Запуск контейнера
```bash
docker run --rm -p 50051:50051 \
  -e MODEL_PATH=/app/models/model.pkl \
  -e MODEL_VERSION=v1.0.0 \
  grpc-ml-service
```

### Проверка эндпоинтов внутри Docker
- Проверка `/health` через grpcurl:
  ```bash
  grpcurl -plaintext localhost:50051 mlservice.v1.PredictionService.Health
  # {
  #   "status": "ok",
  #   "modelVersion": "v1.0.0"
  # }
  ```
- Проверка `/predict` через клиента:
  ```bash
  python -m client.client --host localhost --port 50051
  # {"prediction": "1", "confidence": 0.92, "modelVersion": "v1.0.0"}
  ```

## Скриншоты и сдача
Добавьте в репозиторий или в архив скриншоты вывода команд `grpcurl` и клиента после запуска контейнера (`docker run`). Этого достаточно для демонстрации работоспособности решения.
