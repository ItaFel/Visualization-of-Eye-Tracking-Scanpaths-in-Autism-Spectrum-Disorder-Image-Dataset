from pathlib import Path
from typing import Dict

import torch
from PIL import Image
from torchvision import transforms


def load_model(model_path: Path) -> torch.jit.ScriptModule:
    model = torch.jit.load(str(model_path))
    model.eval()
    return model


def build_preprocess(input_size: int = 224) -> transforms.Compose:
    imagenet_mean = [0.485, 0.456, 0.406]
    imagenet_std = [0.229, 0.224, 0.225]
    return transforms.Compose(
        [
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=imagenet_mean, std=imagenet_std),
        ]
    )


def infer_single_image(model: torch.jit.ScriptModule, image_path: Path) -> Dict[str, float]:
    preprocess = build_preprocess()
    image = Image.open(image_path).convert("RGB")
    tensor = preprocess(image).unsqueeze(0)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=1).squeeze(0)
    return {
        "prob_non_asd": float(probs[0]),
        "prob_asd": float(probs[1]),
        "predicted_class": "ASD (TS)" if probs[1] > probs[0] else "Non-ASD (TC)",
    }


if __name__ == "__main__":
    model = load_model(Path("artifacts/mobilenet_eye_tracking_mobile.pt"))
    stats = infer_single_image(model, Path("Images/TCImages/TC001_39.png"))
    print(stats)
