import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tenrec.data import iter_user_blocks, split_counts_for_user


HIST_COLUMNS = [f"hist_{index}" for index in range(1, 11)]
PADDING_VALUES = {"", "0", "\\N"}


def is_real_hist_item(value: str) -> bool:
    return value not in PADDING_VALUES


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = max(0, min(len(sorted_values) - 1, math.ceil(q * len(sorted_values)) - 1))
    return sorted_values[index]


def rate_summary(rates: list[float]) -> dict:
    if not rates:
        return {
            "user_count": 0,
            "mean": None,
            "median": None,
            "p90": None,
            "p99": None,
            "max": None,
            "gt_5pct_user_count": 0,
            "gt_5pct_user_rate": None,
            "gt_10pct_user_count": 0,
            "gt_10pct_user_rate": None,
        }
    gt_5 = sum(1 for value in rates if value > 0.05)
    gt_10 = sum(1 for value in rates if value > 0.10)
    return {
        "user_count": len(rates),
        "mean": sum(rates) / len(rates),
        "median": percentile(rates, 0.50),
        "p90": percentile(rates, 0.90),
        "p99": percentile(rates, 0.99),
        "max": max(rates),
        "gt_5pct_user_count": gt_5,
        "gt_5pct_user_rate": gt_5 / len(rates),
        "gt_10pct_user_count": gt_10,
        "gt_10pct_user_rate": gt_10 / len(rates),
    }


def split_block(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    counts = split_counts_for_user(len(rows))
    train_end = counts.train
    valid_end = counts.train + counts.valid
    return rows[:train_end], rows[train_end:valid_end], rows[valid_end:]


def hist_items_from_rows(rows: list[dict]) -> set[str]:
    items = set()
    for row in rows:
        for column in HIST_COLUMNS:
            value = row[column]
            if is_real_hist_item(value):
                items.add(value)
    return items


def target_items_from_rows(rows: list[dict]) -> set[str]:
    return {row["item_id"] for row in rows if row["item_id"] not in PADDING_VALUES}


def update_overlap_stats(
    train_hist_set: set[str],
    target_set: set[str],
    rates: list[float],
    totals: dict,
) -> None:
    if not target_set:
        return
    overlap_count = len(train_hist_set & target_set)
    rates.append(overlap_count / len(target_set))
    totals["target_items"] += len(target_set)
    totals["overlap_items"] += overlap_count


def validate_columns(input_path: Path) -> None:
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
    required = {"user_id", "item_id", *HIST_COLUMNS}
    missing = sorted(required - fieldnames)
    if missing:
        raise ValueError(f"Missing required columns in {input_path}: {missing}")


def check_hist_leakage(
    input_path: Path,
    hist_sample_size: int,
    progress_every_rows: int,
) -> dict:
    validate_columns(input_path)
    started_at = time.time()
    item_universe = set()
    hist_sample = []
    hist_non_padding_seen = 0
    valid_rates = []
    test_rates = []
    valid_totals = {"target_items": 0, "overlap_items": 0}
    test_totals = {"target_items": 0, "overlap_items": 0}
    user_blocks = 0
    total_rows = 0
    users_with_valid = 0
    users_with_test = 0
    next_progress = progress_every_rows

    for _, rows in iter_user_blocks(input_path):
        user_blocks += 1
        total_rows += len(rows)
        train_rows, valid_rows, test_rows = split_block(rows)
        train_hist_set = hist_items_from_rows(train_rows)
        valid_target_set = target_items_from_rows(valid_rows)
        test_target_set = target_items_from_rows(test_rows)
        if train_rows and valid_target_set:
            users_with_valid += 1
            update_overlap_stats(train_hist_set, valid_target_set, valid_rates, valid_totals)
        if train_rows and test_target_set:
            users_with_test += 1
            update_overlap_stats(train_hist_set, test_target_set, test_rates, test_totals)

        for row in rows:
            item_id = row["item_id"]
            if item_id not in PADDING_VALUES:
                item_universe.add(item_id)
            for column in HIST_COLUMNS:
                value = row[column]
                if is_real_hist_item(value):
                    hist_non_padding_seen += 1
                    if len(hist_sample) < hist_sample_size:
                        hist_sample.append(value)

        if progress_every_rows > 0 and total_rows >= next_progress:
            elapsed = time.time() - started_at
            print(
                f"progress rows={total_rows:,} users={user_blocks:,} "
                f"elapsed={elapsed:.1f}s",
                flush=True,
            )
            while next_progress <= total_rows:
                next_progress += progress_every_rows

    hist_in_universe = sum(1 for value in hist_sample if value in item_universe)
    hist_outside_universe = len(hist_sample) - hist_in_universe
    combined_target_items = valid_totals["target_items"] + test_totals["target_items"]
    combined_overlap_items = valid_totals["overlap_items"] + test_totals["overlap_items"]
    valid_summary = rate_summary(valid_rates)
    test_summary = rate_summary(test_rates)
    worst_mean = max(
        value for value in [valid_summary["mean"], test_summary["mean"]] if value is not None
    )
    worst_p99 = max(
        value for value in [valid_summary["p99"], test_summary["p99"]] if value is not None
    )
    if worst_mean < 0.01 and worst_p99 < 0.05:
        gate = "PASS"
    elif worst_mean > 0.05 or worst_p99 > 0.10:
        gate = "FAIL"
    else:
        gate = "MARGINAL"

    return {
        "input_path": str(input_path),
        "elapsed_seconds": time.time() - started_at,
        "total_rows": total_rows,
        "user_blocks": user_blocks,
        "hist_columns": HIST_COLUMNS,
        "padding_values": sorted(PADDING_VALUES),
        "split_logic": "tenrec.data.split_counts_for_user",
        "check1_train_hist_future_target_overlap": {
            "valid": {
                **valid_summary,
                "users_with_train_and_valid": users_with_valid,
                "global_overlap_items": valid_totals["overlap_items"],
                "global_target_items": valid_totals["target_items"],
                "global_overlap_rate": (
                    valid_totals["overlap_items"] / valid_totals["target_items"]
                    if valid_totals["target_items"]
                    else None
                ),
            },
            "test": {
                **test_summary,
                "users_with_train_and_test": users_with_test,
                "global_overlap_items": test_totals["overlap_items"],
                "global_target_items": test_totals["target_items"],
                "global_overlap_rate": (
                    test_totals["overlap_items"] / test_totals["target_items"]
                    if test_totals["target_items"]
                    else None
                ),
            },
            "combined_valid_test": {
                "global_overlap_items": combined_overlap_items,
                "global_target_items": combined_target_items,
                "global_overlap_rate": (
                    combined_overlap_items / combined_target_items
                    if combined_target_items
                    else None
                ),
            },
        },
        "check2_hist_item_universe_sample": {
            "item_universe_unique_count": len(item_universe),
            "hist_non_padding_seen": hist_non_padding_seen,
            "hist_sample_size_requested": hist_sample_size,
            "hist_sample_size_actual": len(hist_sample),
            "hist_sample_method": "first_non_padding_values_in_file_order",
            "hist_sample_in_item_universe": hist_in_universe,
            "hist_sample_outside_item_universe": hist_outside_universe,
            "hist_sample_in_item_universe_rate": (
                hist_in_universe / len(hist_sample) if hist_sample else None
            ),
            "hist_sample_outside_item_universe_rate": (
                hist_outside_universe / len(hist_sample) if hist_sample else None
            ),
        },
        "gate": {
            "decision": gate,
            "worst_split_mean_overlap_rate": worst_mean,
            "worst_split_p99_overlap_rate": worst_p99,
            "criteria": {
                "PASS": "mean overlap_rate < 1% and p99 < 5%",
                "MARGINAL": "mean overlap_rate 1-5% or p99 5-10%",
                "FAIL": "mean overlap_rate > 5% or p99 > 10%",
            },
        },
    }


def fmt_rate(value) -> str:
    if value is None:
        return "NA"
    return f"{value:.6%}"


def fmt_number(value) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.10f}"
    return f"{value:,}"


def make_markdown_report(result: dict) -> str:
    check1 = result["check1_train_hist_future_target_overlap"]
    check2 = result["check2_hist_item_universe_sample"]
    gate = result["gate"]
    lines = [
        "# Hist Leakage Check",
        "",
        "## Scope",
        "",
        f"- input: `{result['input_path']}`",
        f"- total rows: {result['total_rows']:,}",
        f"- user blocks: {result['user_blocks']:,}",
        f"- split logic: `{result['split_logic']}`",
        f"- hist columns: `{', '.join(result['hist_columns'])}`",
        f"- padding values excluded: `{', '.join(result['padding_values'])}`",
        "",
        "## Gate Criteria",
        "",
        "- PASS: mean overlap_rate < 1% and p99 < 5%",
        "- MARGINAL: mean overlap_rate 1-5% or p99 5-10%",
        "- FAIL: mean overlap_rate > 5% or p99 > 10%",
        "",
        "## Check 1: train hist vs future valid/test target item overlap",
        "",
        "| split | users | mean | median | p90 | p99 | max | users >5% | users >10% | global overlap items | global target items | global overlap rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ("valid", "test"):
        summary = check1[split]
        lines.append(
            f"| {split} | {summary['user_count']:,} | {fmt_rate(summary['mean'])} | "
            f"{fmt_rate(summary['median'])} | {fmt_rate(summary['p90'])} | "
            f"{fmt_rate(summary['p99'])} | {fmt_rate(summary['max'])} | "
            f"{summary['gt_5pct_user_count']:,} ({fmt_rate(summary['gt_5pct_user_rate'])}) | "
            f"{summary['gt_10pct_user_count']:,} ({fmt_rate(summary['gt_10pct_user_rate'])}) | "
            f"{summary['global_overlap_items']:,} | {summary['global_target_items']:,} | "
            f"{fmt_rate(summary['global_overlap_rate'])} |"
        )
    combined = check1["combined_valid_test"]
    lines.extend(
        [
            "",
            "Combined valid+test global overlap:",
            "",
            f"- overlap items: {combined['global_overlap_items']:,}",
            f"- target items: {combined['global_target_items']:,}",
            f"- overlap rate: {fmt_rate(combined['global_overlap_rate'])}",
            "",
            "## Check 2: hist item sample vs full item universe",
            "",
            f"- full-file unique item_id count: {check2['item_universe_unique_count']:,}",
            f"- non-padding hist values seen: {check2['hist_non_padding_seen']:,}",
            f"- sample method: `{check2['hist_sample_method']}`",
            f"- sample size: {check2['hist_sample_size_actual']:,} / {check2['hist_sample_size_requested']:,}",
            f"- sample in item universe: {check2['hist_sample_in_item_universe']:,} ({fmt_rate(check2['hist_sample_in_item_universe_rate'])})",
            f"- sample outside item universe: {check2['hist_sample_outside_item_universe']:,} ({fmt_rate(check2['hist_sample_outside_item_universe_rate'])})",
            "",
            "## Gate Decision",
            "",
            f"- decision: **{gate['decision']}**",
            f"- worst split mean overlap_rate: {fmt_rate(gate['worst_split_mean_overlap_rate'])}",
            f"- worst split p99 overlap_rate: {fmt_rate(gate['worst_split_p99_overlap_rate'])}",
            "",
            "## Interpretation Boundary",
            "",
            "- This check does not prove the original Tenrec hist construction is time-correct.",
            "- It checks the practical leakage risk under this project's strict user-order split.",
            "- If the gate is PASS, hist is operationally safe for the next DIN implementation step under this split.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check whether train hist_1..hist_10 leak future valid/test target items."
    )
    parser.add_argument(
        "--input",
        default="data/Tenrec/ctr_data_1M.csv",
        help="Raw Tenrec CTR CSV path.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/inspection",
        help="Directory for JSON and Markdown reports.",
    )
    parser.add_argument(
        "--hist-sample-size",
        type=int,
        default=1_000_000,
        help="Number of non-padding hist values to sample for item-universe check.",
    )
    parser.add_argument(
        "--progress-every-rows",
        type=int,
        default=5_000_000,
        help="Print progress every N rows; set 0 to disable.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = check_hist_leakage(
        input_path=input_path,
        hist_sample_size=args.hist_sample_size,
        progress_every_rows=args.progress_every_rows,
    )
    json_path = output_dir / "hist_leakage_check.json"
    md_path = output_dir / "hist_leakage_check.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(make_markdown_report(result), encoding="utf-8")

    valid = result["check1_train_hist_future_target_overlap"]["valid"]
    test = result["check1_train_hist_future_target_overlap"]["test"]
    combined = result["check1_train_hist_future_target_overlap"]["combined_valid_test"]
    check2 = result["check2_hist_item_universe_sample"]
    gate = result["gate"]
    print("hist leakage check complete")
    print(f"rows={result['total_rows']:,} users={result['user_blocks']:,}")
    print(
        "valid "
        f"mean={fmt_rate(valid['mean'])} p99={fmt_rate(valid['p99'])} "
        f"global={fmt_rate(valid['global_overlap_rate'])}"
    )
    print(
        "test "
        f"mean={fmt_rate(test['mean'])} p99={fmt_rate(test['p99'])} "
        f"global={fmt_rate(test['global_overlap_rate'])}"
    )
    print(
        "combined "
        f"overlap_items={combined['global_overlap_items']:,} "
        f"target_items={combined['global_target_items']:,} "
        f"global={fmt_rate(combined['global_overlap_rate'])}"
    )
    print(
        "hist sample "
        f"in_universe={check2['hist_sample_in_item_universe']:,}/"
        f"{check2['hist_sample_size_actual']:,} "
        f"({fmt_rate(check2['hist_sample_in_item_universe_rate'])})"
    )
    print(f"gate={gate['decision']}")
    print(f"json={json_path}")
    print(f"markdown={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
