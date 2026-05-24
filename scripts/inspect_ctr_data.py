import argparse
import csv
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path


DISTRIBUTION_COLUMNS = [
    "click",
    "follow",
    "like",
    "share",
    "watching_times",
    "gender",
    "age",
    "video_category",
]
HISTORY_COLUMNS = [f"hist_{idx}" for idx in range(1, 11)]
TIMESTAMP_COLUMN_CANDIDATES = {
    "timestamp",
    "time",
    "ts",
    "event_time",
    "click_time",
    "exposure_time",
}


def percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * quantile) - 1)
    return ordered[index]


def count_summary(counter):
    counts = list(counter.values())
    if not counts:
        return {"min": None, "p50": None, "p90": None, "p99": None, "max": None}
    return {
        "min": min(counts),
        "p50": percentile(counts, 0.50),
        "p90": percentile(counts, 0.90),
        "p99": percentile(counts, 0.99),
        "max": max(counts),
    }


def counter_to_dict(counter):
    return dict(counter)


def inspect_file(input_path, progress_interval=0):
    input_path = Path(input_path)
    started_at = time.time()

    distributions = {column: Counter() for column in DISTRIBUTION_COLUMNS}
    user_counts = Counter()
    item_counts = Counter()
    history_stats = {
        column: {"empty_count": 0, "zero_count": 0, "nonzero_count": 0}
        for column in HISTORY_COLUMNS
    }
    nonzero_history_lengths = Counter()
    target_item_in_history_count = 0
    bad_width_rows = 0
    total_rows = 0

    with input_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        columns = next(reader)
        column_indexes = {column: idx for idx, column in enumerate(columns)}
        expected_width = len(columns)

        missing_required = [
            column
            for column in ["user_id", "item_id", *DISTRIBUTION_COLUMNS, *HISTORY_COLUMNS]
            if column not in column_indexes
        ]
        if missing_required:
            raise ValueError(f"Missing required columns: {', '.join(missing_required)}")

        for row in reader:
            if len(row) != expected_width:
                bad_width_rows += 1
                continue

            total_rows += 1
            user_id = row[column_indexes["user_id"]]
            item_id = row[column_indexes["item_id"]]
            user_counts[user_id] += 1
            item_counts[item_id] += 1

            for column in DISTRIBUTION_COLUMNS:
                distributions[column][row[column_indexes[column]]] += 1

            row_history_nonzero = 0
            row_history_values = []
            for column in HISTORY_COLUMNS:
                value = row[column_indexes[column]]
                row_history_values.append(value)
                if value == "":
                    history_stats[column]["empty_count"] += 1
                elif value == "0":
                    history_stats[column]["zero_count"] += 1
                else:
                    history_stats[column]["nonzero_count"] += 1
                    row_history_nonzero += 1

            nonzero_history_lengths[str(row_history_nonzero)] += 1
            if item_id in row_history_values:
                target_item_in_history_count += 1

            if progress_interval and total_rows % progress_interval == 0:
                elapsed = time.time() - started_at
                print(
                    f"processed_rows={total_rows:,} bad_width_rows={bad_width_rows:,} elapsed_seconds={elapsed:.1f}",
                    file=sys.stderr,
                    flush=True,
                )

    timestamp_columns = [
        column
        for column in columns
        if column.lower() in TIMESTAMP_COLUMN_CANDIDATES
    ]
    elapsed_seconds = time.time() - started_at

    return {
        "file": {
            "path": str(input_path),
            "size_bytes": input_path.stat().st_size,
            "size_gb_decimal": round(input_path.stat().st_size / 1_000_000_000, 4),
            "size_gib": round(input_path.stat().st_size / (1024 ** 3), 4),
            "columns": columns,
            "total_rows": total_rows,
            "bad_width_rows": bad_width_rows,
            "elapsed_seconds": round(elapsed_seconds, 3),
        },
        "distributions": {
            column: counter_to_dict(distributions[column])
            for column in DISTRIBUTION_COLUMNS
        },
        "ids": {
            "unique_user_id": len(user_counts),
            "unique_item_id": len(item_counts),
            "user_row_count_summary": count_summary(user_counts),
            "item_row_count_summary": count_summary(item_counts),
        },
        "history": {
            **history_stats,
            "nonzero_history_length_distribution": counter_to_dict(nonzero_history_lengths),
            "target_item_in_history_count": target_item_in_history_count,
            "target_item_in_history_rate": (
                round(target_item_in_history_count / total_rows, 8)
                if total_rows
                else None
            ),
        },
        "risk": {
            "has_explicit_timestamp": bool(timestamp_columns),
            "timestamp_columns": timestamp_columns,
            "split_note": (
                "没有显式 timestamp，不能直接做 timestamp-based split；"
                "下一步需要验证是否可使用 user-level chronological / order-based split。"
            ),
            "history_leakage_note": (
                "hist_1 到 hist_10 是否只来自 target event 之前的行为仍需验证，"
                "当前 inspection 只能检查字段形态和 target item 是否出现在 history。"
            ),
        },
    }


def top_items(distribution, limit=20):
    return sorted(distribution.items(), key=lambda item: (-item[1], item[0]))[:limit]


def format_distribution(distribution, limit=20):
    items = top_items(distribution, limit=limit)
    return ", ".join(f"`{key}`: {value:,}" for key, value in items)


def render_report(summary):
    file_info = summary["file"]
    ids = summary["ids"]
    history = summary["history"]
    risk = summary["risk"]
    lines = [
        "# ctr_data_1M.csv inspection report",
        "",
        "## 文件基础信息",
        "",
        f"- path: `{file_info['path']}`",
        f"- size bytes: `{file_info['size_bytes']:,}`",
        f"- size GB decimal: `{file_info['size_gb_decimal']}`",
        f"- size GiB: `{file_info['size_gib']}`",
        f"- total rows: `{file_info['total_rows']:,}`",
        f"- bad width rows: `{file_info['bad_width_rows']:,}`",
        f"- elapsed seconds: `{file_info['elapsed_seconds']}`",
        f"- columns: `{', '.join(file_info['columns'])}`",
        "",
        "## Label / behavior 分布",
        "",
    ]
    for column, distribution in summary["distributions"].items():
        lines.append(f"- `{column}`: {format_distribution(distribution)}")

    lines.extend(
        [
            "",
            "## ID 统计",
            "",
            f"- unique `user_id`: `{ids['unique_user_id']:,}`",
            f"- unique `item_id`: `{ids['unique_item_id']:,}`",
            f"- user row count summary: `{ids['user_row_count_summary']}`",
            f"- item row count summary: `{ids['item_row_count_summary']}`",
            "",
            "## History 字段检查",
            "",
        ]
    )
    for column in HISTORY_COLUMNS:
        stats = history[column]
        lines.append(
            f"- `{column}`: empty `{stats['empty_count']:,}`, "
            f"zero `{stats['zero_count']:,}`, nonzero `{stats['nonzero_count']:,}`"
        )
    lines.extend(
        [
            f"- nonzero history length distribution: `{history['nonzero_history_length_distribution']}`",
            f"- target item in history count: `{history['target_item_in_history_count']:,}`",
            f"- target item in history rate: `{history['target_item_in_history_rate']}`",
            "",
            "## 初步风险判断",
            "",
            f"- has explicit timestamp: `{risk['has_explicit_timestamp']}`",
            f"- timestamp columns: `{risk['timestamp_columns']}`",
            f"- split note: {risk['split_note']}",
            f"- history leakage note: {risk['history_leakage_note']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(summary, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "ctr_data_1M_summary.json"
    report_path = output_dir / "ctr_data_1M_report.md"

    with summary_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    report_path.write_text(render_report(summary), encoding="utf-8", newline="\n")
    return summary_path, report_path


def parse_args():
    parser = argparse.ArgumentParser(description="Stream inspect Tenrec ctr_data_1M.csv.")
    parser.add_argument("--input", required=True, help="Path to ctr_data_1M.csv")
    parser.add_argument("--output-dir", required=True, help="Directory for JSON and Markdown outputs")
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=1_000_000,
        help="Print progress every N valid rows. Use 0 to disable.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    summary = inspect_file(args.input, progress_interval=args.progress_interval)
    summary_path, report_path = write_outputs(summary, args.output_dir)
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
