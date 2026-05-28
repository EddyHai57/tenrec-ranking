import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tenrec.data import preprocess_ctr


def parse_args():
    parser = argparse.ArgumentParser(description="Two-pass CTR preprocessing for Tenrec.")
    parser.add_argument("--config", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = Path(args.config)
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    metadata = preprocess_ctr(
        input_path=Path(config["input_path"]),
        output_root=Path(config["output_root"]),
        config=config,
    )
    print(json.dumps(
        {
            "run_id": metadata["run_id"],
            "metadata_path": str(Path(metadata["pass2"]["split_paths"]["train"]).parents[1] / "metadata.json"),
            "split_rows": metadata["pass2"]["split_rows"],
            "vocab_sizes": metadata["vocab_sizes"],
            "sequence_features": metadata.get("sequence_features", {}),
            "oov_counts": metadata["pass2"]["oov_counts"],
            "missing_counts": metadata["pass2"]["missing_counts"],
            "sequence_oov_counts": metadata["pass2"].get("sequence_oov_counts", {}),
            "sequence_padding_counts": metadata["pass2"].get("sequence_padding_counts", {}),
            "pass1_elapsed_seconds": metadata["pass1"]["elapsed_seconds"],
            "pass2_elapsed_seconds": metadata["pass2"]["elapsed_seconds"],
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
