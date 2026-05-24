import argparse
import csv
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path


TINY_SAMPLE_NAME = "ctr_tiny_100k_head.csv"
USER_BLOCK_SAMPLE_NAME = "ctr_user_block_1m_seed20260525.csv"
SUMMARY_NAME = "ctr_smoke_samples_summary.json"
REPORT_NAME = "ctr_smoke_samples_report.md"


def stable_hash(seed, value):
    payload = f"{seed}:{value}".encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, int((len(ordered) * quantile + 0.999999999)) - 1)
    return ordered[index]


def count_summary(values):
    if not values:
        return {"min": None, "p50": None, "p90": None, "p99": None, "max": None}
    return {
        "min": min(values),
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p99": percentile(values, 0.99),
        "max": max(values),
    }


def counter_to_dict(counter):
    return dict(counter)


def file_size(path):
    return Path(path).stat().st_size


def finalize_block(blocks, user_id, row_count, click_counts):
    if user_id is None:
        return
    blocks.append(
        {
            "user_id": user_id,
            "row_count": row_count,
            "click_counts": dict(click_counts),
        }
    )


def first_pass(input_path, tiny_path, tiny_rows, progress_interval=1_000_000):
    started_at = time.time()
    blocks = []
    total_rows = 0
    tiny_written_rows = 0
    tiny_click_counts = Counter()
    tiny_users = set()

    current_user = None
    current_user_rows = 0
    current_click_counts = Counter()

    with input_path.open("r", newline="", encoding="utf-8") as source, tiny_path.open(
        "w", newline="", encoding="utf-8"
    ) as tiny_target:
        reader = csv.reader(source)
        writer = csv.writer(tiny_target, lineterminator="\n")
        header = next(reader)
        column_indexes = {column: idx for idx, column in enumerate(header)}
        for required in ("user_id", "click"):
            if required not in column_indexes:
                raise ValueError(f"Missing required column: {required}")
        user_idx = column_indexes["user_id"]
        click_idx = column_indexes["click"]

        writer.writerow(header)

        for row in reader:
            total_rows += 1
            user_id = row[user_idx]
            click = row[click_idx]

            if tiny_written_rows < tiny_rows:
                writer.writerow(row)
                tiny_written_rows += 1
                tiny_click_counts[click] += 1
                tiny_users.add(user_id)

            if user_id != current_user:
                finalize_block(blocks, current_user, current_user_rows, current_click_counts)
                current_user = user_id
                current_user_rows = 0
                current_click_counts = Counter()

            current_user_rows += 1
            current_click_counts[click] += 1

            if progress_interval and total_rows % progress_interval == 0:
                elapsed = time.time() - started_at
                print(
                    f"first_pass_rows={total_rows:,} user_blocks={len(blocks):,} elapsed_seconds={elapsed:.1f}",
                    file=sys.stderr,
                    flush=True,
                )

        finalize_block(blocks, current_user, current_user_rows, current_click_counts)

    return {
        "header": header,
        "total_rows": total_rows,
        "blocks": blocks,
        "tiny": {
            "actual_rows": tiny_written_rows,
            "user_count": len(tiny_users),
            "click_distribution": counter_to_dict(tiny_click_counts),
        },
        "elapsed_seconds": round(time.time() - started_at, 3),
    }


def choose_user_blocks(blocks, target_rows, seed):
    ordered = sorted(blocks, key=lambda block: (stable_hash(seed, block["user_id"]), block["user_id"]))
    selected_user_ids = set()
    selected_blocks = []
    actual_rows = 0
    click_counts = Counter()

    for block in ordered:
        if actual_rows >= target_rows:
            break
        selected_user_ids.add(block["user_id"])
        selected_blocks.append(block)
        actual_rows += block["row_count"]
        click_counts.update(block["click_counts"])

    return selected_user_ids, selected_blocks, actual_rows, click_counts


def write_user_block_sample(input_path, output_path, selected_user_ids, progress_interval=1_000_000):
    started_at = time.time()
    written_rows = 0
    selected_seen_users = set()
    click_counts = Counter()

    with input_path.open("r", newline="", encoding="utf-8") as source, output_path.open(
        "w", newline="", encoding="utf-8"
    ) as target:
        reader = csv.reader(source)
        writer = csv.writer(target, lineterminator="\n")
        header = next(reader)
        column_indexes = {column: idx for idx, column in enumerate(header)}
        user_idx = column_indexes["user_id"]
        click_idx = column_indexes["click"]
        writer.writerow(header)

        for row_number, row in enumerate(reader, start=1):
            user_id = row[user_idx]
            if user_id in selected_user_ids:
                writer.writerow(row)
                written_rows += 1
                selected_seen_users.add(user_id)
                click_counts[row[click_idx]] += 1

            if progress_interval and row_number % progress_interval == 0:
                elapsed = time.time() - started_at
                print(
                    f"second_pass_rows={row_number:,} written_rows={written_rows:,} elapsed_seconds={elapsed:.1f}",
                    file=sys.stderr,
                    flush=True,
                )

    return {
        "actual_rows": written_rows,
        "user_count": len(selected_seen_users),
        "click_distribution": counter_to_dict(click_counts),
        "elapsed_seconds": round(time.time() - started_at, 3),
    }


def render_report(summary):
    tiny = summary["samples"]["tiny_head"]
    block = summary["samples"]["user_block"]
    lines = [
        "# CTR smoke samples report",
        "",
        "## 输入",
        "",
        f"- input path: `{summary['input_path']}`",
        f"- seed: `{summary['seed']}`",
        f"- generated at: `{summary['generated_at']}`",
        "",
        "## tiny head sample",
        "",
        f"- output path: `{tiny['output_path']}`",
        f"- actual rows: `{tiny['actual_rows']:,}`",
        f"- user count: `{tiny['user_count']:,}`",
        f"- file size bytes: `{tiny['file_size_bytes']:,}`",
        f"- click distribution: `{tiny['click_distribution']}`",
        f"- header preserved: `{tiny['header_preserved']}`",
        f"- shuffled rows: `{tiny['shuffled_rows']}`",
        f"- deduplicated: `{tiny['deduplicated']}`",
        "",
        "## user-block sample",
        "",
        f"- output path: `{block['output_path']}`",
        f"- target rows: `{block['target_rows']:,}`",
        f"- actual rows: `{block['actual_rows']:,}`",
        f"- user count: `{block['user_count']:,}`",
        f"- file size bytes: `{block['file_size_bytes']:,}`",
        f"- click distribution: `{block['click_distribution']}`",
        f"- user row count summary: `{block['user_row_count_summary']}`",
        f"- complete user blocks: `{block['complete_user_blocks']}`",
        f"- header preserved: `{block['header_preserved']}`",
        f"- shuffled rows: `{block['shuffled_rows']}`",
        f"- deduplicated: `{block['deduplicated']}`",
        "",
        "## 使用限制",
        "",
        "- smoke sample 不能作为正式实验结果。",
        "- `ctr_tiny_100k_head.csv` 有明显顺序 / user 偏置，只用于快速 debug。",
        "- `ctr_user_block_1m_seed20260525.csv` 是开发样本，不是 full validation / full test。",
        "- 两个 sample 都不打乱、不去重，不改变原始行内容。",
        "",
    ]
    return "\n".join(lines)


def write_reports(summary, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / SUMMARY_NAME
    report_path = output_dir / REPORT_NAME
    with summary_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    report_path.write_text(render_report(summary), encoding="utf-8", newline="\n")
    return summary_path, report_path


def make_samples(input_path, sample_dir, output_dir, tiny_rows, target_rows, seed):
    input_path = Path(input_path)
    sample_dir = Path(sample_dir)
    output_dir = Path(output_dir)
    sample_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    tiny_path = sample_dir / TINY_SAMPLE_NAME
    user_block_path = sample_dir / USER_BLOCK_SAMPLE_NAME

    first = first_pass(input_path, tiny_path, tiny_rows)
    selected_user_ids, selected_blocks, selected_rows, selected_click_counts = choose_user_blocks(
        first["blocks"], target_rows, seed
    )
    second = write_user_block_sample(input_path, user_block_path, selected_user_ids)

    if second["actual_rows"] != selected_rows:
        raise RuntimeError(
            f"Written user-block rows mismatch: expected {selected_rows}, got {second['actual_rows']}"
        )
    if second["click_distribution"] != counter_to_dict(selected_click_counts):
        raise RuntimeError("Written user-block click distribution does not match selected metadata")

    command = (
        f"python scripts/make_ctr_smoke_samples.py --input {input_path} "
        f"--sample-dir {sample_dir} --output-dir {output_dir} "
        f"--tiny-rows {tiny_rows} --target-rows {target_rows} --seed {seed}"
    )
    block_row_counts = [block["row_count"] for block in selected_blocks]
    summary = {
        "input_path": str(input_path),
        "seed": seed,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "command": command,
        "source": {
            "total_rows_observed": first["total_rows"],
            "user_blocks_observed": len(first["blocks"]),
            "first_pass_elapsed_seconds": first["elapsed_seconds"],
            "second_pass_elapsed_seconds": second["elapsed_seconds"],
        },
        "samples": {
            "tiny_head": {
                "name": TINY_SAMPLE_NAME,
                "output_path": str(tiny_path),
                "requested_rows": tiny_rows,
                "actual_rows": first["tiny"]["actual_rows"],
                "user_count": first["tiny"]["user_count"],
                "click_distribution": first["tiny"]["click_distribution"],
                "file_size_bytes": file_size(tiny_path),
                "header_preserved": True,
                "complete_user_blocks": False,
                "shuffled_rows": False,
                "deduplicated": False,
                "intended_use": "CSV reader、feature parsing、batch shape、最小 metric 流程 smoke debug。",
                "not_for": "正式实验结果或模型指标。",
            },
            "user_block": {
                "name": USER_BLOCK_SAMPLE_NAME,
                "output_path": str(user_block_path),
                "target_rows": target_rows,
                "actual_rows": second["actual_rows"],
                "user_count": second["user_count"],
                "click_distribution": second["click_distribution"],
                "file_size_bytes": file_size(user_block_path),
                "user_row_count_summary": count_summary(block_row_counts),
                "header_preserved": True,
                "complete_user_blocks": True,
                "shuffled_rows": False,
                "deduplicated": False,
                "selection_method": "stable hash over user_id with fixed seed; original row order preserved on write.",
                "intended_use": "dataloader、GAUC、user-level split、order-based split 和 tiny training / overfit smoke。",
                "not_for": "full validation / full test 或正式实验结果。",
            },
        },
    }
    write_reports(summary, output_dir)
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Make Tenrec CTR smoke samples.")
    parser.add_argument("--input", required=True, help="Path to data/Tenrec/ctr_data_1M.csv")
    parser.add_argument("--sample-dir", required=True, help="Directory for sample CSV files")
    parser.add_argument("--output-dir", required=True, help="Directory for sample reports")
    parser.add_argument("--tiny-rows", type=int, default=100_000)
    parser.add_argument("--target-rows", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=20260525)
    return parser.parse_args()


def main():
    args = parse_args()
    summary = make_samples(
        input_path=args.input,
        sample_dir=args.sample_dir,
        output_dir=args.output_dir,
        tiny_rows=args.tiny_rows,
        target_rows=args.target_rows,
        seed=args.seed,
    )
    print(f"Wrote {summary['samples']['tiny_head']['output_path']}")
    print(f"Wrote {summary['samples']['user_block']['output_path']}")
    print(f"Wrote {Path(args.output_dir) / SUMMARY_NAME}")
    print(f"Wrote {Path(args.output_dir) / REPORT_NAME}")


if __name__ == "__main__":
    main()
