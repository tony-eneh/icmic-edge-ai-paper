#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportMissingModuleSource=false
"""
Uncertainty-aware edge AI routing experiment using Kaggle's Ships in Satellite
Imagery dataset (ShipsNet).

Expected dataset source:
https://www.kaggle.com/datasets/rhammell/ships-in-satellite-imagery

The script replaces the earlier CIFAR proxy with a maritime vessel-detection
workflow. It trains a small binary ResNet-18 classifier on ShipsNet, extracts
confidence traces from held-out satellite chips, creates an adverse maritime
condition through deterministic weather/visibility corruption, and evaluates
local/offload/fallback routing policies under stable, intermittent, and degraded
network conditions.
"""

from __future__ import annotations
from tqdm import tqdm
from torchvision import models, transforms
from torch.utils.data import DataLoader, Dataset, Subset
from torch.nn.functional import softmax
from PIL import Image, ImageEnhance, ImageFilter
import torch.nn as nn
import torch
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import argparse
import json
import os
import random
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")


warnings.filterwarnings("ignore")

SEED = 42
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
KAGGLE_DATASET = "rhammell/ships-in-satellite-imagery"


@dataclass(frozen=True)
class ShipSample:
    image: Image.Image
    label: int
    scene_id: str
    location: str
    source: str


class ShipsNetDataset(Dataset):
    def __init__(
        self,
        samples: list[ShipSample],
        transform: transforms.Compose,
        adverse: bool = False,
    ) -> None:
        self.samples = samples
        self.transform = transform
        self.adverse = adverse

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        sample = self.samples[index]
        image = sample.image.copy()
        if self.adverse:
            image = apply_adverse_maritime_condition(image, index)
        return self.transform(image), sample.label


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run maritime uncertainty-aware routing experiments with ShipsNet."
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("data/ships-in-satellite-imagery"),
        help="Directory containing shipsnet.json or an extracted shipsnet/ image folder.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory where result CSV files and figures are written.",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--max-confidence-samples", type=int, default=500)
    parser.add_argument("--tasks-per-scenario", type=int, default=2500)
    parser.add_argument("--adverse-fraction", type=float, default=0.4)
    parser.add_argument("--safety-sensitive-fraction", type=float, default=0.3)
    parser.add_argument("--conf-threshold", type=float, default=0.65)
    parser.add_argument("--confidence-only-threshold",
                        type=float, default=0.70)
    parser.add_argument("--bw-threshold", type=float, default=1.8)
    parser.add_argument("--unsafe-confidence-threshold",
                        type=float, default=0.60)
    parser.add_argument(
        "--fine-tune-backbone",
        action="store_true",
        help="Train the full ResNet-18 instead of only the classifier head.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Optional checkpoint path. If it exists, load it; after training, save to it.",
    )
    parser.add_argument(
        "--no-download-dataset",
        action="store_true",
        help="Do not attempt Kaggle download when --dataset-root is missing.",
    )
    return parser.parse_args()


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_shipsnet_samples(dataset_root: Path, allow_download: bool = True) -> list[ShipSample]:
    dataset_root = prepare_dataset_root(dataset_root, allow_download)

    if not dataset_root.exists():
        raise FileNotFoundError(
            f"Dataset root not found: {dataset_root}\n"
            f"{dataset_setup_instructions(dataset_root)}"
        )

    json_path = find_file(dataset_root, "shipsnet.json")
    if json_path is not None:
        return load_samples_from_json(json_path)

    image_dir = dataset_root / "shipsnet"
    shipsnet_zip = find_file(dataset_root, "shipsnet.zip")
    if not image_dir.exists() and shipsnet_zip is not None:
        extract_zip(shipsnet_zip, image_dir)

    if image_dir.exists():
        return load_samples_from_images(image_dir)

    image_files = [path for path in dataset_root.rglob(
        "*") if path.suffix.lower() in IMAGE_SUFFIXES]
    if image_files:
        return load_samples_from_images(dataset_root)

    raise RuntimeError(
        f"No ShipsNet data found under {dataset_root}. Expected shipsnet.json, "
        f"shipsnet.zip, or PNG images.\n{dataset_setup_instructions(dataset_root)}"
    )


def prepare_dataset_root(dataset_root: Path, allow_download: bool) -> Path:
    if dataset_root.exists():
        return dataset_root

    archive_path = dataset_root.with_suffix(".zip")
    if archive_path.exists():
        dataset_root.mkdir(parents=True, exist_ok=True)
        extract_zip(archive_path, dataset_root)
    elif allow_download:
        download_kaggle_dataset(dataset_root)
    return dataset_root


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def configure_kaggle_credentials(repo_root: Path) -> None:
    load_env_file(repo_root / ".env")
    load_env_file(Path.cwd() / ".env")

    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return

    token = os.environ.get("KAGGLE_API_TOKEN")
    if not token:
        return

    token_payload = read_kaggle_token_payload(token)
    if not token_payload:
        username = os.environ.get("KAGGLE_USERNAME")
        if username:
            os.environ.setdefault("KAGGLE_KEY", token)
        else:
            print(
                "Found KAGGLE_API_TOKEN, but it looks like an API key only. "
                "Add KAGGLE_USERNAME=<your_kaggle_username> to .env, or set "
                "KAGGLE_API_TOKEN to the full kaggle.json content."
            )
        return

    username = token_payload.get("username")
    key = token_payload.get("key")
    if username and key:
        os.environ.setdefault("KAGGLE_USERNAME", str(username))
        os.environ.setdefault("KAGGLE_KEY", str(key))


def read_kaggle_token_payload(token: str) -> dict[str, str] | None:
    possible_path = Path(token).expanduser()
    if possible_path.exists():
        try:
            return json.loads(possible_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    try:
        payload = json.loads(token)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def download_kaggle_dataset(dataset_root: Path) -> None:
    if dataset_root.exists():
        return
    if not (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY")):
        return

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError as exc:
        raise RuntimeError(
            "Kaggle credentials were found, but the kaggle package is not installed. "
            "Run `pip install -r requirements.txt` and try again."
        ) from exc

    dataset_root.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Kaggle dataset {KAGGLE_DATASET} -> {dataset_root}")
    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files(KAGGLE_DATASET, path=str(
        dataset_root), unzip=True, quiet=False)


def extract_zip(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {zip_path} -> {destination}")
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)


def dataset_setup_instructions(dataset_root: Path) -> str:
    return (
        "Download Kaggle's Ships in Satellite Imagery dataset into the repo first.\n"
        "This script can auto-download it when .env contains either:\n"
        "  KAGGLE_USERNAME=<your_username> and KAGGLE_KEY=<your_key>\n"
        "or:\n"
        "  KAGGLE_USERNAME=<your_username> and KAGGLE_API_TOKEN=<your_key>\n"
        "or:\n"
        "  KAGGLE_API_TOKEN='{\"username\":\"...\",\"key\":\"...\"}'\n"
        "You can also download it manually with Kaggle CLI:\n"
        f"  kaggle datasets download -d {KAGGLE_DATASET} -p {dataset_root.as_posix()} --unzip\n"
        "Then rerun:\n"
        f"  python experiments/run_edge_ai_routing_experiments.py --dataset-root {dataset_root.as_posix()}\n"
        "If Kaggle CLI is not installed/configured, run `pip install -r requirements.txt`."
    )


def find_file(root: Path, name: str) -> Path | None:
    direct = root / name
    if direct.exists():
        return direct
    matches = list(root.rglob(name))
    return matches[0] if matches else None


def load_samples_from_json(json_path: Path) -> list[ShipSample]:
    print(f"Loading ShipsNet JSON: {json_path}")
    with json_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    data = payload["data"]
    labels = payload["labels"]
    scene_ids = payload.get("scene_ids", ["unknown"] * len(labels))
    locations = payload.get("locations", ["unknown"] * len(labels))

    samples = []
    for index, pixels in enumerate(tqdm(data, desc="Decoding ShipsNet JSON")):
        array = np.asarray(pixels, dtype=np.uint8).reshape(
            3, 80, 80).transpose(1, 2, 0)
        image = Image.fromarray(array, mode="RGB")
        samples.append(
            ShipSample(
                image=image,
                label=int(labels[index]),
                scene_id=str(scene_ids[index]),
                location=str(locations[index]),
                source=f"json:{index}",
            )
        )
    return samples


def load_samples_from_images(image_root: Path) -> list[ShipSample]:
    print(f"Loading ShipsNet images from: {image_root}")
    samples = []
    for path in tqdm(sorted(image_root.rglob("*")), desc="Reading image files"):
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        label = infer_label_from_filename(path)
        if label is None:
            continue
        parts = path.stem.split("_")
        scene_id = parts[1] if len(parts) > 1 else "unknown"
        location = "_".join(parts[2:]) if len(parts) > 2 else "unknown"
        samples.append(
            ShipSample(
                image=Image.open(path).convert("RGB"),
                label=label,
                scene_id=scene_id,
                location=location,
                source=str(path),
            )
        )
    if not samples:
        raise RuntimeError(
            f"No labeled ShipsNet image files found in {image_root}")
    return samples


def infer_label_from_filename(path: Path) -> int | None:
    token = path.stem.split("_")[0]
    if token in {"0", "1"}:
        return int(token)
    return None


def stratified_split(
    samples: list[ShipSample], train_fraction: float, val_fraction: float
) -> tuple[list[int], list[int], list[int]]:
    by_label: dict[int, list[int]] = {0: [], 1: []}
    for index, sample in enumerate(samples):
        by_label[sample.label].append(index)

    rng = random.Random(SEED)
    train_indices: list[int] = []
    val_indices: list[int] = []
    test_indices: list[int] = []
    for label_indices in by_label.values():
        rng.shuffle(label_indices)
        train_end = int(len(label_indices) * train_fraction)
        val_end = train_end + int(len(label_indices) * val_fraction)
        train_indices.extend(label_indices[:train_end])
        val_indices.extend(label_indices[train_end:val_end])
        test_indices.extend(label_indices[val_end:])

    rng.shuffle(train_indices)
    rng.shuffle(val_indices)
    rng.shuffle(test_indices)
    return train_indices, val_indices, test_indices


def build_transforms() -> tuple[transforms.Compose, transforms.Compose]:
    train_transform = transforms.Compose(
        [
            transforms.Resize((112, 112)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(15),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[
                                 0.229, 0.224, 0.225]),
        ]
    )
    eval_transform = transforms.Compose(
        [
            transforms.Resize((112, 112)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[
                                 0.229, 0.224, 0.225]),
        ]
    )
    return train_transform, eval_transform


def apply_adverse_maritime_condition(image: Image.Image, index: int) -> Image.Image:
    rng = random.Random(SEED + index)
    image = ImageEnhance.Contrast(image).enhance(rng.uniform(0.45, 0.75))
    image = ImageEnhance.Brightness(image).enhance(rng.uniform(0.55, 0.85))
    image = image.filter(ImageFilter.GaussianBlur(
        radius=rng.uniform(0.6, 1.4)))

    array = np.asarray(image).astype(np.float32)
    haze = np.full_like(array, 205.0)
    alpha = rng.uniform(0.16, 0.32)
    array = (1.0 - alpha) * array + alpha * haze
    noise = np.random.default_rng(SEED + index).normal(0, 8, size=array.shape)
    array = np.clip(array + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(array, mode="RGB")


def build_model(device: torch.device, train_backbone: bool) -> nn.Module:
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    model.fc = nn.Linear(model.fc.in_features, 2)
    if not train_backbone:
        for name, parameter in model.named_parameters():
            parameter.requires_grad = name.startswith("fc.")
    return model.to(device)


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    args: argparse.Namespace,
    device: torch.device,
) -> nn.Module:
    if args.checkpoint and args.checkpoint.exists():
        print(f"Loading classifier checkpoint: {args.checkpoint}")
        model.load_state_dict(torch.load(args.checkpoint, map_location=device))
        return model

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad], lr=args.lr
    )

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        for images, labels in tqdm(train_loader, desc=f"Training epoch {epoch}/{args.epochs}"):
            images = images.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * labels.size(0)
            train_correct += (logits.argmax(dim=1) == labels).sum().item()
            train_total += labels.size(0)

        val_acc, val_loss = evaluate_classifier(
            model, val_loader, criterion, device)
        print(
            f"  Epoch {epoch}: train_loss={train_loss / train_total:.4f}, "
            f"train_acc={train_correct / train_total:.3f}, "
            f"val_loss={val_loss:.4f}, val_acc={val_acc:.3f}"
        )

    if args.checkpoint:
        args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), args.checkpoint)
        print(f"Saved classifier checkpoint: {args.checkpoint}")
    return model


def evaluate_classifier(
    model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device
) -> tuple[float, float]:
    model.eval()
    correct = 0
    total = 0
    total_loss = 0.0
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            logits = model(images)
            loss = criterion(logits, labels)
            total_loss += loss.item() * labels.size(0)
            correct += (logits.argmax(dim=1) == labels).sum().item()
            total += labels.size(0)
    return correct / max(total, 1), total_loss / max(total, 1)


def build_confidence_traces(
    model: nn.Module,
    samples: list[ShipSample],
    test_indices: list[int],
    eval_transform: transforms.Compose,
    args: argparse.Namespace,
    device: torch.device,
) -> pd.DataFrame:
    model.eval()
    selected_indices = test_indices[: args.max_confidence_samples]
    rows = []
    with torch.no_grad():
        for index in tqdm(selected_indices, desc="Extracting confidence traces"):
            sample = samples[index]
            for condition, adverse in (("nominal", False), ("adverse", True)):
                image = sample.image.copy()
                if adverse:
                    image = apply_adverse_maritime_condition(image, index)
                tensor = eval_transform(image).unsqueeze(0).to(device)
                logits = model(tensor)
                probs = softmax(logits, dim=1).squeeze(0)
                confidence = float(probs.max().item())
                predicted = int(probs.argmax().item())
                entropy = float(-torch.sum(probs *
                                torch.log(probs + 1e-8)).item())
                rows.append(
                    {
                        "sample_index": index,
                        "label": sample.label,
                        "predicted": predicted,
                        "correct": predicted == sample.label,
                        "confidence": confidence,
                        "entropy": entropy,
                        "condition": condition,
                        "is_ood": adverse,
                        "scene_id": sample.scene_id,
                        "location": sample.location,
                        "source": sample.source,
                    }
                )
    return pd.DataFrame(rows)


def plot_decision_boundary(args: argparse.Namespace, output_dir: Path) -> None:
    confidence_grid = np.linspace(0.05, 0.99, 60)
    bandwidth_grid = np.linspace(0.1, 10.0, 60)
    rows = []
    for confidence in confidence_grid:
        for bandwidth in bandwidth_grid:
            task = {"confidence": confidence,
                    "bandwidth": bandwidth, "peer_available": True}
            rows.append(
                {
                    "confidence": confidence,
                    "bandwidth": bandwidth,
                    "action": policy_three_way(task, args.conf_threshold, args.bw_threshold),
                }
            )
    boundary = pd.DataFrame(rows)
    action_map = {"local": 0, "offload": 1, "fallback": 2}
    fig, ax = plt.subplots(figsize=(6, 5))
    scatter = ax.scatter(
        boundary["confidence"],
        boundary["bandwidth"],
        c=boundary["action"].map(action_map),
        cmap="RdYlGn",
        s=12,
        alpha=0.85,
    )
    ax.axvline(args.conf_threshold, linestyle="--", color="gray", alpha=0.7)
    ax.axhline(args.bw_threshold, linestyle="--", color="gray", alpha=0.7)
    ax.set_xlabel("Vessel classifier confidence")
    ax.set_ylabel("Effective bandwidth (Mbps)")
    ax.set_title("Three-way routing regions")
    cbar = plt.colorbar(scatter, ticks=[0, 1, 2])
    cbar.ax.set_yticklabels(["Local", "Offload", "Fallback"])
    plt.tight_layout()
    plt.savefig(output_dir / "decision_boundary.pdf",
                dpi=150, bbox_inches="tight")
    plt.close()


def generate_task(confidence_traces: pd.DataFrame, args: argparse.Namespace) -> dict[str, object]:
    adverse = random.random() < args.adverse_fraction
    pool = confidence_traces[confidence_traces["is_ood"] == adverse]
    if pool.empty:
        pool = confidence_traces
    row = pool.sample(n=1, random_state=random.randint(0, 2**31 - 1)).iloc[0]
    confidence = float(
        np.clip(row["confidence"] + np.random.normal(0, 0.015), 0.01, 0.99))
    return {
        "confidence": confidence,
        "entropy": float(row["entropy"]),
        "is_ood": bool(row["is_ood"]),
        "condition": row["condition"],
        "label": int(row["label"]),
        "predicted": int(row["predicted"]),
        "correct": bool(row["correct"]),
        "safety_sensitive": random.random() < args.safety_sensitive_fraction,
    }


def simulate_network(scenario: str) -> tuple[float, bool, float, float]:
    if scenario == "stable":
        return np.random.uniform(5, 12), random.random() > 0.1, 0.03, 20.0
    if scenario == "intermittent":
        return np.random.uniform(0.8, 6), random.random() > 0.3, 0.12, 40.0
    return np.random.uniform(0.2, 2.5), random.random() > 0.6, 0.30, 80.0


def policy_always_local(task: dict[str, object]) -> str:
    return "local"


def policy_always_offload(task: dict[str, object]) -> str:
    return "offload" if task["peer_available"] else "local"


def policy_confidence_threshold(task: dict[str, object], threshold: float) -> str:
    return "offload" if float(task["confidence"]) < threshold else "local"


def policy_load_only(task: dict[str, object]) -> str:
    return "offload" if float(task["queue_pressure"]) > 0.5 and task["peer_available"] else "local"


def policy_three_way(task: dict[str, object], conf_threshold: float, bw_threshold: float) -> str:
    confidence = float(task["confidence"])
    bandwidth = float(task["bandwidth"])
    peer_available = bool(task["peer_available"])
    if confidence < conf_threshold and bandwidth < bw_threshold:
        return "fallback"
    if bandwidth > bw_threshold and peer_available:
        return "offload"
    return "local"


def compute_cost(
    action: str, task: dict[str, object], loss_rate: float, latency_base: float, args: argparse.Namespace
) -> tuple[float, bool, float]:
    confidence = float(task["confidence"])
    safety_sensitive = bool(task["safety_sensitive"])
    bandwidth = float(task["bandwidth"])
    peer_available = bool(task["peer_available"])
    model_wrong = not bool(task["correct"])

    if action == "local":
        latency = 35 + (1 - confidence) * 80
        is_unsafe = safety_sensitive and (
            confidence < args.unsafe_confidence_threshold or model_wrong)
        energy = 0.5
    elif action == "offload":
        if not peer_available or random.random() < loss_rate:
            latency = 180 + latency_base
            is_unsafe = safety_sensitive
            energy = 0.8
        else:
            latency = latency_base + (50 / max(bandwidth, 0.2))
            is_unsafe = False
            energy = 0.6
    else:
        latency = 45.0
        is_unsafe = False
        energy = 0.2
    return latency, is_unsafe, energy


def run_routing_experiment(confidence_traces: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    policies = {
        "Always Local": policy_always_local,
        "Always Offload": policy_always_offload,
        "Confidence Threshold": lambda task: policy_confidence_threshold(
            task, args.confidence_only_threshold
        ),
        "Load Only": policy_load_only,
        "Three-Way (Ours)": lambda task: policy_three_way(
            task, args.conf_threshold, args.bw_threshold
        ),
    }
    results = []
    for scenario in ["stable", "intermittent", "degraded"]:
        print(f"  Running {scenario} scenario...")
        for policy_name, policy_fn in policies.items():
            for _ in range(args.tasks_per_scenario):
                task = generate_task(confidence_traces, args)
                bandwidth, peer_available, loss_rate, latency_base = simulate_network(
                    scenario)
                queue_pressure = np.random.beta(
                    2, 5) if scenario == "stable" else np.random.beta(5, 2)
                task.update(
                    {
                        "bandwidth": bandwidth,
                        "peer_available": peer_available,
                        "queue_pressure": queue_pressure,
                    }
                )
                action = policy_fn(task)
                latency, is_unsafe, energy = compute_cost(
                    action, task, loss_rate, latency_base, args)
                results.append(
                    {
                        "policy": policy_name,
                        "scenario": scenario,
                        "action": action,
                        "latency": latency,
                        "is_unsafe": is_unsafe,
                        "energy": energy,
                        "confidence": task["confidence"],
                        "entropy": task["entropy"],
                        "is_ood": task["is_ood"],
                        "condition": task["condition"],
                        "label": task["label"],
                        "predicted": task["predicted"],
                        "correct": task["correct"],
                    }
                )
    return pd.DataFrame(results)


def summarize_results(df_results: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary = df_results.groupby(["policy", "scenario"]).agg(
        {"latency": "mean", "is_unsafe": "mean", "energy": "mean"}
    )
    summary = summary.round(3)
    summary.columns = ["Latency (ms)", "Unsafe Rate", "Energy (J)"]

    action_dist = df_results.groupby(
        ["policy", "scenario", "action"]).size().unstack(fill_value=0)
    action_dist_pct = action_dist.div(
        action_dist.sum(axis=1), axis=0).round(3) * 100

    summary.to_csv(output_dir / "results_summary.csv")
    action_dist_pct.to_csv(output_dir / "action_distribution.csv")
    df_results.to_csv(output_dir / "full_results.csv", index=False)
    return summary, action_dist_pct


def plot_fallback_analysis(df_results: pd.DataFrame, args: argparse.Namespace, output_dir: Path) -> None:
    three_way = df_results[df_results["policy"] == "Three-Way (Ours)"]
    fallback_tasks = three_way[three_way["action"] == "fallback"]
    print(f"Total fallback events: {len(fallback_tasks)}")
    print(f"Fallback rate: {len(fallback_tasks) / max(len(three_way), 1):.2%}")

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    axes[0].hist(fallback_tasks["confidence"], bins=20,
                 edgecolor="black", color="red", alpha=0.7)
    axes[0].axvline(args.conf_threshold, linestyle="--",
                    color="blue", label="Confidence threshold")
    axes[0].set_xlabel("Vessel classifier confidence")
    axes[0].set_ylabel("Fallback count")
    axes[0].set_title("(a) Confidence at fallback")
    axes[0].legend(fontsize=8)

    scenario_fallback = three_way.groupby("scenario")["action"].apply(
        lambda values: (values == "fallback").mean())
    scenario_fallback.reindex(["stable", "intermittent", "degraded"]).plot(
        kind="bar", ax=axes[1], color=["green", "orange", "red"]
    )
    axes[1].set_xlabel("Network scenario")
    axes[1].set_ylabel("Fallback rate")
    axes[1].set_title("(b) Fallback by scenario")
    axes[1].set_ylim(0, max(0.5, float(scenario_fallback.max()) + 0.05))

    action_by_condition = three_way.groupby(
        ["condition", "action"]).size().unstack(fill_value=0)
    action_by_condition = action_by_condition.div(
        action_by_condition.sum(axis=1), axis=0)
    action_by_condition = action_by_condition.reindex(
        ["nominal", "adverse"], fill_value=0.0)
    for action in ["local", "offload", "fallback"]:
        if action not in action_by_condition.columns:
            action_by_condition[action] = 0.0

    bottom = np.zeros(len(action_by_condition))
    colors = {"local": "green", "offload": "blue", "fallback": "red"}
    x = np.arange(len(action_by_condition))
    for action in ["local", "offload", "fallback"]:
        values = action_by_condition[action].to_numpy()
        axes[2].bar(x, values, bottom=bottom,
                    label=action.title(), color=colors[action])
        bottom += values
    axes[2].set_xticks(x)
    axes[2].set_xticklabels([label.title()
                            for label in action_by_condition.index])
    axes[2].set_ylabel("Action rate")
    axes[2].set_title("(c) Actions by image condition")
    axes[2].legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(output_dir / "fallback_analysis.pdf",
                dpi=150, bbox_inches="tight")
    plt.close()


def write_latex_table(summary: pd.DataFrame, action_dist_pct: pd.DataFrame, output_dir: Path) -> None:
    intermittent = summary[summary.index.get_level_values(
        "scenario") == "intermittent"]
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Performance comparison under intermittent maritime connectivity}",
        "\\label{tab:main_results}",
        "\\footnotesize",
        "\\begin{tabular}{@{}lcccc@{}}",
        "\\toprule",
        "\\textbf{Policy} & \\textbf{Latency (ms)} & \\textbf{Unsafe Rate} & \\textbf{Energy (J)} & \\textbf{Fallback Rate} \\\\",
        "\\midrule",
    ]
    for policy in intermittent.index.get_level_values("policy").unique():
        row = intermittent.loc[(policy, "intermittent")]
        fallback_pct = 0.0
        if "fallback" in action_dist_pct.columns:
            fallback_pct = float(
                action_dist_pct.loc[(policy, "intermittent"), "fallback"])
        lines.append(
            f"{policy} & {row['Latency (ms)']:.1f} & {row['Unsafe Rate']:.1%} & "
            f"{row['Energy (J)']:.2f} & {fallback_pct / 100:.1%} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    (output_dir / "latex_table.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_key_statistics(df_results: pd.DataFrame) -> None:
    three_way = df_results[df_results["policy"] == "Three-Way (Ours)"]
    always_local = df_results[df_results["policy"] == "Always Local"]
    confidence_threshold = df_results[df_results["policy"]
                                      == "Confidence Threshold"]
    three_way_int = three_way[three_way["scenario"] == "intermittent"]
    local_int = always_local[always_local["scenario"] == "intermittent"]
    threshold_int = confidence_threshold[confidence_threshold["scenario"]
                                         == "intermittent"]

    local_unsafe = local_int["is_unsafe"].mean()
    threshold_unsafe = threshold_int["is_unsafe"].mean()
    ours_unsafe = three_way_int["is_unsafe"].mean()
    reduction_vs_local = 0.0 if local_unsafe == 0 else (
        local_unsafe - ours_unsafe) / local_unsafe
    reduction_vs_threshold = 0.0 if threshold_unsafe == 0 else (
        threshold_unsafe - ours_unsafe) / threshold_unsafe

    print("\n" + "=" * 60)
    print("KEY STATISTICS FOR PAPER")
    print("=" * 60)
    print("\nUnder intermittent connectivity:")
    print(f"  - Three-way unsafe rate: {ours_unsafe:.1%}")
    print(f"  - Always local unsafe rate: {local_unsafe:.1%}")
    print(f"  - Confidence threshold unsafe rate: {threshold_unsafe:.1%}")
    print(f"  - Unsafe reduction vs. always local: {reduction_vs_local:.1%}")
    print(
        f"  - Unsafe reduction vs. confidence threshold: {reduction_vs_threshold:.1%}")
    print(
        f"  - Fallback rate: {(three_way_int['action'] == 'fallback').mean():.1%}")

    print("\nThree-Way by image condition:")
    for condition, group in three_way.groupby("condition"):
        print(
            f"  - {condition}: confidence={group['confidence'].mean():.3f}, "
            f"fallback={(group['action'] == 'fallback').mean():.1%}, "
            f"unsafe={group['is_unsafe'].mean():.1%}"
        )


def main() -> None:
    args = parse_args()
    set_seed()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[1]
    configure_kaggle_credentials(repo_root)

    print("=" * 60)
    print("ShipsNet Edge AI Routing Experiments")
    print("=" * 60)
    print(f"Dataset root: {args.dataset_root}")
    print(f"Output dir: {args.output_dir.resolve()}")

    samples = load_shipsnet_samples(
        args.dataset_root, allow_download=not args.no_download_dataset)
    labels = pd.Series([sample.label for sample in samples]
                       ).value_counts().sort_index()
    print(f"Loaded {len(samples)} image chips")
    print(f"Class counts: no-ship={labels.get(0, 0)}, ship={labels.get(1, 0)}")

    train_indices, val_indices, test_indices = stratified_split(
        samples, args.train_fraction, args.val_fraction
    )
    print(
        f"Split sizes: train={len(train_indices)}, val={len(val_indices)}, test={len(test_indices)}"
    )

    train_transform, eval_transform = build_transforms()
    train_dataset = Subset(ShipsNetDataset(
        samples, train_transform), train_indices)
    val_dataset = Subset(ShipsNetDataset(samples, eval_transform), val_indices)
    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    model = build_model(device, args.fine_tune_backbone)

    print("\n[1/5] Training maritime vessel classifier...")
    model = train_model(model, train_loader, val_loader, args, device)

    print("\n[2/5] Extracting nominal and adverse-condition confidence traces...")
    confidence_traces = build_confidence_traces(
        model, samples, test_indices, eval_transform, args, device)
    confidence_traces.to_csv(
        args.output_dir / "confidence_traces.csv", index=False)
    print(confidence_traces.groupby("condition")[
          "confidence"].agg(["count", "mean", "std"]).to_string())
    print(confidence_traces.groupby("condition")[
          "correct"].mean().rename("accuracy").to_string())

    print("\n[3/5] Plotting routing decision boundary...")
    plot_decision_boundary(args, args.output_dir)
    print("  Saved: decision_boundary.pdf")

    print("\n[4/5] Running routing baseline comparison...")
    df_results = run_routing_experiment(confidence_traces, args)
    print(f"  Total tasks processed: {len(df_results)}")
    summary, action_dist_pct = summarize_results(df_results, args.output_dir)
    print(summary.to_string())

    print("\n[5/5] Plotting fallback analysis and writing paper table...")
    plot_fallback_analysis(df_results, args, args.output_dir)
    write_latex_table(summary, action_dist_pct, args.output_dir)
    print_key_statistics(df_results)

    print("\nGenerated files:")
    print("  - confidence_traces.csv")
    print("  - decision_boundary.pdf")
    print("  - fallback_analysis.pdf")
    print("  - results_summary.csv")
    print("  - action_distribution.csv")
    print("  - full_results.csv")
    print("  - latex_table.txt")
    print("\nEXPERIMENTS COMPLETE")


if __name__ == "__main__":
    main()
