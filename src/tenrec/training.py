import copy
import json
import math
import random
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from tenrec.metrics import binary_auc, binary_log_loss, impression_weighted_gauc
from tenrec.models import build_model
from tenrec.torch_data import (
    ensure_shuffled_train,
    iter_materialized_batches,
    load_first_batches,
    load_metadata,
    raw_feature_columns,
    split_path,
)


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(device_name: str) -> torch.device:
    if device_name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_name)


def train_base_logit(metadata: dict) -> float:
    label_counts = metadata["pass2"]["label_counts"]["train"]
    positive_count = float(label_counts.get("1", 0))
    negative_count = float(label_counts.get("0", 0))
    if positive_count <= 0 or negative_count <= 0:
        raise ValueError("Cannot compute train base logit from single-class train labels")
    return math.log(positive_count / negative_count)


def resolve_model_config(config: dict, metadata: dict) -> dict:
    model_config = copy.deepcopy(config["model"])
    if model_config.get("name") == "dcnv2":
        dcnv2_config = model_config.get("dcnv2", {})
        if dcnv2_config.get("output_bias_init") == "train_base_rate":
            dcnv2_config["output_bias_init"] = train_base_logit(metadata)
    return model_config


def make_run_id(config: dict) -> str:
    model_name = config["model"]["name"]
    run_name = config["run"]["name"]
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{run_name}-{model_name}"


def prepare_run_dir(config: dict, run_id: str) -> Path:
    run_dir = Path(config["run"]["output_dir"]) / run_id
    (run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    return run_dir


def train_one_epoch(model, criterion, optimizer, train_path, feature_columns, config, device):
    model.train()
    total_loss = 0.0
    total_rows = 0
    for batch in iter_materialized_batches(
        path=train_path,
        feature_columns=feature_columns,
        batch_size=int(config["data"]["batch_size"]),
        device=device,
        max_rows=config["data"].get("max_train_rows"),
    ):
        labels = batch["labels"]
        logits = model(batch["features"])
        loss = criterion(logits, labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        rows = labels.numel()
        total_loss += float(loss.detach().cpu()) * rows
        total_rows += rows
    if total_rows == 0:
        raise ValueError("No train rows were read")
    return total_loss / total_rows


@torch.no_grad()
def evaluate(model, valid_path, feature_columns, config, device):
    model.eval()
    labels = []
    scores = []
    groups = []
    total_loss = 0.0
    total_rows = 0
    criterion = nn.BCEWithLogitsLoss()
    for batch in iter_materialized_batches(
        path=valid_path,
        feature_columns=feature_columns,
        batch_size=int(config["data"]["eval_batch_size"]),
        device=device,
        max_rows=config["data"].get("max_valid_rows"),
    ):
        logits = model(batch["features"])
        loss = criterion(logits, batch["labels"])
        probabilities = torch.sigmoid(logits)
        rows = batch["labels"].numel()
        total_loss += float(loss.detach().cpu()) * rows
        total_rows += rows
        labels.extend(batch["labels"].detach().cpu().numpy().astype(int).tolist())
        scores.extend(probabilities.detach().cpu().numpy().tolist())
        groups.extend(batch["features"]["user_id"].detach().cpu().numpy().tolist())
    if total_rows == 0:
        raise ValueError("No valid rows were read")
    gauc = impression_weighted_gauc(labels, scores, groups)
    return {
        "rows": total_rows,
        "loss": total_loss / total_rows,
        "auc": binary_auc(labels, scores),
        "logloss": binary_log_loss(labels, scores),
        "gauc": gauc.gauc,
        "gauc_valid_user_count": gauc.valid_user_count,
        "gauc_total_user_count": gauc.total_user_count,
        "gauc_valid_row_count": gauc.valid_row_count,
        "gauc_total_row_count": gauc.total_row_count,
        "gauc_row_coverage_rate": gauc.row_coverage_rate,
    }


@torch.no_grad()
def evaluate_path(model, path, feature_columns, batch_size, max_rows, device):
    model.eval()
    labels = []
    scores = []
    groups = []
    total_loss = 0.0
    total_rows = 0
    criterion = nn.BCEWithLogitsLoss()
    for batch in iter_materialized_batches(
        path=path,
        feature_columns=feature_columns,
        batch_size=batch_size,
        device=device,
        max_rows=max_rows,
    ):
        logits = model(batch["features"])
        loss = criterion(logits, batch["labels"])
        probabilities = torch.sigmoid(logits)
        rows = batch["labels"].numel()
        total_loss += float(loss.detach().cpu()) * rows
        total_rows += rows
        labels.extend(batch["labels"].detach().cpu().numpy().astype(int).tolist())
        scores.extend(probabilities.detach().cpu().numpy().tolist())
        groups.extend(batch["features"]["user_id"].detach().cpu().numpy().tolist())
    if total_rows == 0:
        raise ValueError(f"No rows were read from {path}")
    gauc = impression_weighted_gauc(labels, scores, groups)
    return {
        "rows": total_rows,
        "loss": total_loss / total_rows,
        "auc": binary_auc(labels, scores),
        "logloss": binary_log_loss(labels, scores),
        "gauc": gauc.gauc,
        "gauc_valid_user_count": gauc.valid_user_count,
        "gauc_total_user_count": gauc.total_user_count,
        "gauc_valid_row_count": gauc.valid_row_count,
        "gauc_total_row_count": gauc.total_row_count,
        "gauc_row_coverage_rate": gauc.row_coverage_rate,
    }


def save_checkpoint(path: Path, model, optimizer, state: dict) -> None:
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            **state,
        },
        path,
    )


def better_metric(value: float, best: float | None, mode: str) -> bool:
    if best is None:
        return True
    if mode == "min":
        return value < best
    if mode == "max":
        return value > best
    raise ValueError(f"Unsupported metric mode: {mode}")


def run_training(config: dict) -> dict:
    set_seed(int(config["run"]["seed"]))
    device = resolve_device(config["run"].get("device", "auto"))
    metadata_path = Path(config["data"]["metadata_path"])
    metadata = load_metadata(metadata_path)
    feature_columns = raw_feature_columns(metadata)
    vocab_sizes = {column: int(metadata["vocab_sizes"][column]) for column in feature_columns}
    run_id = make_run_id(config)
    run_dir = prepare_run_dir(config, run_id)

    if config["data"].get("train_shuffle", "materialized") == "materialized":
        train_path = ensure_shuffled_train(
            metadata_path=metadata_path,
            seed=int(config["run"]["seed"]),
            bucket_count=int(config["data"]["shuffle_bucket_count"]),
        )
    else:
        train_path = split_path(metadata, "train")
    valid_path = split_path(metadata, "valid")

    model_config = resolve_model_config(config, metadata)
    model = build_model(model_config, vocab_sizes, feature_columns).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=float(config["train"]["lr"]),
        weight_decay=float(config["train"].get("weight_decay", 0.0)),
    )

    metrics_path = run_dir / "metrics.jsonl"
    best_metric = None
    best_epoch = None
    bad_epochs = 0
    metric_name = config["train"]["checkpoint_metric"]
    metric_mode = config["train"]["checkpoint_mode"]
    with metrics_path.open("w", encoding="utf-8", newline="\n") as handle:
        for epoch in range(1, int(config["train"]["epochs"]) + 1):
            train_loss = train_one_epoch(
                model=model,
                criterion=criterion,
                optimizer=optimizer,
                train_path=train_path,
                feature_columns=feature_columns,
                config=config,
                device=device,
            )
            valid_metrics = evaluate(model, valid_path, feature_columns, config, device)
            train_metrics = None
            if config["train"].get("eval_train_metrics", False):
                train_metrics = evaluate_path(
                    model=model,
                    path=train_path,
                    feature_columns=feature_columns,
                    batch_size=int(config["data"]["eval_batch_size"]),
                    max_rows=config["data"].get("max_train_rows"),
                    device=device,
                )
            row = {
                "epoch": epoch,
                "train_loss": train_loss,
                "train": train_metrics,
                "valid": valid_metrics,
                "device": str(device),
                "train_path": str(train_path),
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()

            current_metric = valid_metrics[metric_name]
            if better_metric(current_metric, best_metric, metric_mode):
                best_metric = current_metric
                best_epoch = epoch
                bad_epochs = 0
                save_checkpoint(
                    run_dir / "checkpoints" / "best.pt",
                    model=model,
                    optimizer=optimizer,
                    state={
                        "epoch": epoch,
                        "best_metric": best_metric,
                        "checkpoint_metric": metric_name,
                        "checkpoint_mode": metric_mode,
                        "config": config,
                        "metadata_path": str(metadata_path),
                        "metadata_run_id": metadata["run_id"],
                        "vocab_sizes": vocab_sizes,
                        "git_commit": git_commit(),
                    },
                )
            else:
                bad_epochs += 1
                if bad_epochs >= int(config["train"]["patience"]):
                    break

    summary = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "model": config["model"]["name"],
        "device": str(device),
        "metadata_path": str(metadata_path),
        "metadata_run_id": metadata["run_id"],
        "train_path": str(train_path),
        "valid_path": str(valid_path),
        "best_epoch": best_epoch,
        "best_metric": best_metric,
        "checkpoint_metric": metric_name,
        "checkpoint_path": str(run_dir / "checkpoints" / "best.pt"),
        "git_commit": git_commit(),
        "smoke_only": bool(config["data"].get("max_train_rows") or config["data"].get("max_valid_rows")),
        "class_reweighting": False,
        "resampling": False,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def run_overfit(config: dict) -> dict:
    set_seed(int(config["run"]["seed"]))
    device = resolve_device(config["run"].get("device", "auto"))
    metadata_path = Path(config["data"]["metadata_path"])
    metadata = load_metadata(metadata_path)
    feature_columns = raw_feature_columns(metadata)
    vocab_sizes = {column: int(metadata["vocab_sizes"][column]) for column in feature_columns}
    train_path = split_path(metadata, "train")
    batches = load_first_batches(
        path=train_path,
        feature_columns=feature_columns,
        batch_size=int(config["overfit"]["batch_size"]),
        num_batches=int(config["overfit"]["num_batches"]),
        device=device,
    )
    model_config = resolve_model_config(config, metadata)
    model = build_model(model_config, vocab_sizes, feature_columns).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=float(config["overfit"]["lr"]))
    losses = []
    for _ in range(int(config["overfit"]["epochs"])):
        epoch_loss = 0.0
        rows = 0
        for batch in batches:
            logits = model(batch["features"])
            loss = criterion(logits, batch["labels"])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            batch_rows = batch["labels"].numel()
            epoch_loss += float(loss.detach().cpu()) * batch_rows
            rows += batch_rows
        losses.append(epoch_loss / rows)
    return {
        "model": config["model"]["name"],
        "device": str(device),
        "metadata_path": str(metadata_path),
        "num_batches": int(config["overfit"]["num_batches"]),
        "batch_size": int(config["overfit"]["batch_size"]),
        "initial_loss": losses[0],
        "final_loss": losses[-1],
        "target_loss": float(config["overfit"]["target_loss"]),
        "passed": losses[-1] <= float(config["overfit"]["target_loss"]),
        "losses_tail": losses[-10:],
    }
