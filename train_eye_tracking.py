import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, Subset
from torch.utils.tensorboard import SummaryWriter
from torch.utils.mobile_optimizer import optimize_for_mobile
from torchvision import datasets, models, transforms


def set_seed(seed: int = 42) -> None:
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


@dataclass
class TrainConfig:
    data_dir: Path
    batch_size: int = 16
    num_workers: int = 0
    lr: float = 2e-4
    weight_decay: float = 1e-4
    epochs: int = 35
    val_size: float = 0.15
    test_size: float = 0.15
    seed: int = 42
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    artifacts_dir: Path = Path("artifacts")


def build_transforms(input_size: int = 224) -> Tuple[transforms.Compose, transforms.Compose]:
    imagenet_mean = [0.485, 0.456, 0.406]
    imagenet_std = [0.229, 0.224, 0.225]
    train_tf = transforms.Compose(
        [
            transforms.Resize((input_size, input_size)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.RandomRotation(5),
            transforms.ToTensor(),
            transforms.Normalize(mean=imagenet_mean, std=imagenet_std),
        ]
    )
    eval_tf = transforms.Compose(
        [
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=imagenet_mean, std=imagenet_std),
        ]
    )
    return train_tf, eval_tf


def stratified_split(
    dataset: datasets.ImageFolder, cfg: TrainConfig
) -> Tuple[Subset, Subset, Subset, Dict[int, str]]:
    targets = np.array([target for _, target in dataset.samples])
    idxs = np.arange(len(dataset))

    train_idxs, temp_idxs, train_y, temp_y = train_test_split(
        idxs,
        targets,
        test_size=cfg.val_size + cfg.test_size,
        random_state=cfg.seed,
        stratify=targets,
    )
    relative_test_size = cfg.test_size / (cfg.val_size + cfg.test_size)
    val_idxs, test_idxs, _, _ = train_test_split(
        temp_idxs,
        temp_y,
        test_size=relative_test_size,
        random_state=cfg.seed,
        stratify=temp_y,
    )

    class_idx_to_name = {idx: cls_name for idx, cls_name in enumerate(dataset.classes)}
    return (
        Subset(dataset, train_idxs),
        Subset(dataset, val_idxs),
        Subset(dataset, test_idxs),
        class_idx_to_name,
    )


def build_dataloaders(cfg: TrainConfig) -> Tuple[DataLoader, DataLoader, DataLoader, Dict[int, str]]:
    train_tf, eval_tf = build_transforms()
    train_dataset = datasets.ImageFolder(root=cfg.data_dir, transform=train_tf)
    eval_dataset = datasets.ImageFolder(root=cfg.data_dir, transform=eval_tf)

    train_set, val_set, test_set, idx_to_class = stratified_split(train_dataset, cfg)

    # Align evaluation transforms
    val_set.dataset = eval_dataset
    test_set.dataset = eval_dataset

    def make_loader(split: Subset, shuffle: bool = False) -> DataLoader:
        return DataLoader(
            split,
            batch_size=cfg.batch_size,
            shuffle=shuffle,
            num_workers=cfg.num_workers,
            pin_memory=cfg.device.startswith("cuda"),
        )

    train_loader = make_loader(train_set, shuffle=True)
    val_loader = make_loader(val_set)
    test_loader = make_loader(test_set)
    return train_loader, val_loader, test_loader, idx_to_class


def build_model(num_classes: int) -> nn.Module:
    backbone = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    backbone.classifier[3] = nn.Linear(backbone.classifier[3].in_features, num_classes)
    return backbone


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    loss_fn: nn.Module,
    device: str,
) -> Tuple[float, float]:
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        logits = model(images)
        loss = loss_fn(logits, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    mean_loss = running_loss / total
    accuracy = correct / total
    return mean_loss, accuracy


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, loss_fn: nn.Module, device: str) -> Tuple[float, float]:
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)
        logits = model(images)
        loss = loss_fn(logits, labels)

        running_loss += loss.item() * images.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    mean_loss = running_loss / total
    accuracy = correct / total
    return mean_loss, accuracy


@torch.no_grad()
def predict(model: nn.Module, loader: DataLoader, device: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    all_logits: List[np.ndarray] = []
    all_targets: List[np.ndarray] = []

    for images, labels in loader:
        images = images.to(device)
        logits = model(images)
        all_logits.append(F.softmax(logits, dim=1).cpu().numpy())
        all_targets.append(labels.numpy())

    probs = np.concatenate(all_logits)
    targets = np.concatenate(all_targets)
    preds = probs.argmax(axis=1)
    return preds, targets, probs


def export_mobile_artifacts(
    model: nn.Module,
    device: str,
    sample_size: Tuple[int, int, int],
    export_dir: Path,
) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    model.eval()
    dummy = torch.randn(1, *sample_size, device=device)
    traced = torch.jit.trace(model, dummy)
    scripted = optimize_for_mobile(traced)
    torch.jit.save(scripted, export_dir / "mobilenet_eye_tracking_mobile.pt")


def train(cfg: TrainConfig) -> Dict:
    set_seed(cfg.seed)
    cfg.artifacts_dir.mkdir(exist_ok=True, parents=True)
    writer = SummaryWriter(log_dir=str(cfg.artifacts_dir / "runs"))

    train_loader, val_loader, test_loader, idx_to_class = build_dataloaders(cfg)
    readable_idx_to_class = {
        idx: ("Non-ASD (TC)" if "tc" in name.lower() else "ASD (TS)") for idx, name in idx_to_class.items()
    }
    train_indices: List[int] = train_loader.dataset.indices  # type: ignore[attr-defined]
    base_dataset: datasets.ImageFolder = train_loader.dataset.dataset  # type: ignore[attr-defined]
    train_targets = [base_dataset.samples[i][1] for i in train_indices]
    class_counts = np.bincount(train_targets, minlength=len(idx_to_class))
    class_counts[class_counts == 0] = 1
    class_weights = len(train_targets) / (len(idx_to_class) * class_counts)
    loss_weights = torch.tensor(class_weights, dtype=torch.float32, device=cfg.device)

    model = build_model(num_classes=len(idx_to_class)).to(cfg.device)

    optimizer = AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=cfg.epochs)
    loss_fn = nn.CrossEntropyLoss(weight=loss_weights)

    best_val_acc = 0.0
    best_state = None

    for epoch in range(1, cfg.epochs + 1):
        train_loss, train_acc = train_one_epoch(model, train_loader, optimizer, loss_fn, cfg.device)
        val_loss, val_acc = evaluate(model, val_loader, loss_fn, cfg.device)
        scheduler.step()

        writer.add_scalar("Loss/train", train_loss, epoch)
        writer.add_scalar("Loss/val", val_loss, epoch)
        writer.add_scalar("Accuracy/train", train_acc, epoch)
        writer.add_scalar("Accuracy/val", val_acc, epoch)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {
                "model_state": model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "epoch": epoch,
                "val_acc": val_acc,
            }

        print(
            f"[{epoch:03d}/{cfg.epochs}] "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )

    if best_state is None:
        raise RuntimeError("Не удалось сохранить лучшую модель.")

    model.load_state_dict(best_state["model_state"])
    torch.save(best_state, cfg.artifacts_dir / "best_model_state.pth")

    test_loss, test_acc = evaluate(model, test_loader, loss_fn, cfg.device)
    preds, targets, probs = predict(model, test_loader, cfg.device)

    metrics = classification_report(
        targets,
        preds,
        target_names=[readable_idx_to_class[i] for i in sorted(idx_to_class.keys())],
        output_dict=True,
        digits=4,
    )
    conf_mat = confusion_matrix(targets, preds).tolist()
    try:
        roc_auc = roc_auc_score(targets, probs[:, 1])
    except ValueError:
        roc_auc = None

    export_mobile_artifacts(model, cfg.device, (3, 224, 224), cfg.artifacts_dir)
    torch.save(model.state_dict(), cfg.artifacts_dir / "mobilenet_eye_tracking_state_dict.pth")

    writer.close()

    results = {
        "test_loss": test_loss,
        "test_accuracy": test_acc,
        "classification_report": metrics,
        "confusion_matrix": conf_mat,
        "idx_to_class": idx_to_class,
        "readable_idx_to_class": readable_idx_to_class,
        "best_epoch": best_state["epoch"],
        "val_accuracy_best": best_state["val_acc"],
        "roc_auc": roc_auc,
        "probabilities": probs.tolist(),
        "targets": targets.tolist(),
        "predictions": preds.tolist(),
    }

    with open(cfg.artifacts_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


def parse_args() -> TrainConfig:
    parser = argparse.ArgumentParser(description="Train MobileNetV3 on eye-tracking scanpath images.")
    parser.add_argument("--data-dir", type=Path, default=Path("Images"), help="Корневая директория с подклассами.")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=35)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--val-size", type=float, default=0.15)
    parser.add_argument("--test-size", type=float, default=0.15)
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")

    args = parser.parse_args()
    return TrainConfig(
        data_dir=args.data_dir,
        batch_size=args.batch_size,
        epochs=args.epochs,
        lr=args.lr,
        weight_decay=args.weight_decay,
        val_size=args.val_size,
        test_size=args.test_size,
        seed=args.seed,
        num_workers=args.num_workers,
        device=args.device,
        artifacts_dir=args.artifacts_dir,
    )


def main() -> None:
    cfg = parse_args()
    results = train(cfg)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
