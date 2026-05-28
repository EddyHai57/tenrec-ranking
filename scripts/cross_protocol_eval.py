import argparse
import json
import sys
from pathlib import Path

import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tenrec.metrics import binary_auc, binary_log_loss, impression_weighted_gauc, pcoc
from tenrec.models import build_model
from tenrec.torch_data import (
    iter_tensor_batches,
    load_materialized_tensor_table,
    load_metadata,
    raw_feature_columns,
    sequence_feature_specs,
    split_path,
)


def resolve_device(device_name: str) -> torch.device:
    if device_name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_name)


def checkpoint_model_config(checkpoint: dict) -> dict:
    if "config" not in checkpoint or "model" not in checkpoint["config"]:
        raise ValueError("Checkpoint is missing config.model")
    model_config = json.loads(json.dumps(checkpoint["config"]["model"]))
    model_name = model_config["name"]
    if model_name == "dcnv2":
        dcnv2_config = model_config.get("dcnv2", {})
        if dcnv2_config.get("output_bias_init") == "train_base_rate":
            dcnv2_config["output_bias_init"] = 0.0
    if model_name == "din":
        din_config = model_config.get("din", {})
        if din_config.get("output_bias_init") == "train_base_rate":
            din_config["output_bias_init"] = 0.0
    return model_config


def model_logits(model, batch: dict) -> torch.Tensor:
    if getattr(model, "requires_sequence_features", False):
        return model(batch["features"], batch.get("sequence_features"))
    return model(batch["features"])


@torch.no_grad()
def evaluate_tensor_test(model, test_data, batch_size: int) -> dict:
    model.eval()
    labels = []
    scores = []
    groups = []
    total_loss = 0.0
    total_rows = 0
    sum_pred = 0.0
    sum_label = 0.0
    criterion = nn.BCEWithLogitsLoss()
    for batch in iter_tensor_batches(test_data, batch_size=batch_size, shuffle=False):
        logits = model_logits(model, batch)
        loss = criterion(logits, batch["labels"])
        probabilities = torch.sigmoid(logits)
        rows = batch["labels"].numel()
        total_loss += float(loss.detach().cpu()) * rows
        total_rows += rows
        sum_pred += float(probabilities.detach().sum().cpu())
        sum_label += float(batch["labels"].detach().sum().cpu())
        labels.extend(batch["labels"].detach().cpu().numpy().astype(int).tolist())
        scores.extend(probabilities.detach().cpu().numpy().tolist())
        groups.extend(batch["features"]["user_id"].detach().cpu().numpy().tolist())
    if total_rows == 0:
        raise ValueError("No test rows were read")

    gauc = impression_weighted_gauc(labels, scores, groups)
    return {
        "auc": binary_auc(labels, scores),
        "gauc": gauc.gauc,
        "gauc_row_coverage_rate": gauc.row_coverage_rate,
        "logloss": binary_log_loss(labels, scores),
        "pcoc": pcoc(labels, scores),
        "mean_pred": sum_pred / total_rows,
        "mean_label": sum_label / total_rows,
        "test_rows": total_rows,
    }


def evaluate_checkpoint(
    checkpoint_path: Path,
    metadata_path: Path,
    device_name: str,
    batch_size: int = 32768,
) -> dict:
    device = resolve_device(device_name)
    metadata = load_metadata(metadata_path)
    feature_columns = raw_feature_columns(metadata)
    sequence_features = sequence_feature_specs(metadata)
    vocab_sizes = {column: int(metadata["vocab_sizes"][column]) for column in feature_columns}

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model = build_model(
        model_config=checkpoint_model_config(checkpoint),
        vocab_sizes=vocab_sizes,
        feature_columns=feature_columns,
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])

    test_data = load_materialized_tensor_table(
        path=split_path(metadata, "test"),
        feature_columns=feature_columns,
        device=device,
        sequence_features=sequence_features,
    )
    result = evaluate_tensor_test(model=model, test_data=test_data, batch_size=batch_size)
    result["test_run_id"] = metadata["run_id"]
    return result


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a trained checkpoint on another metadata test split.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
    parser.add_argument("--batch-size", type=int, default=32768)
    return parser.parse_args()


def main():
    args = parse_args()
    result = evaluate_checkpoint(
        checkpoint_path=Path(args.checkpoint),
        metadata_path=Path(args.metadata),
        device_name=args.device,
        batch_size=args.batch_size,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
