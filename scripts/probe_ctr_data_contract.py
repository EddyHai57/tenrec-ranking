import argparse
import csv
import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path


HISTORY_COLUMNS = [f"hist_{idx}" for idx in range(1, 11)]
TIMESTAMP_COLUMN_CANDIDATES = {
    "timestamp",
    "time",
    "ts",
    "event_time",
    "click_time",
    "exposure_time",
}


def stable_int(value):
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * quantile) - 1)
    return ordered[index]


def summarize(values):
    if not values:
        return {"min": None, "p50": None, "p90": None, "p99": None, "max": None}
    return {
        "min": min(values),
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p99": percentile(values, 0.99),
        "max": max(values),
    }


def top_counter(counter, limit=20):
    return dict(counter.most_common(limit))


def make_sample_user_state(user_id):
    return {
        "user_id": user_id,
        "rows": 0,
        "history_items": 0,
        "history_in_previous_any_item": 0,
        "history_in_previous_clicked_item": 0,
        "history_not_in_previous_any_item": 0,
        "target_in_history": 0,
        "previous_any_items": set(),
        "previous_clicked_items": set(),
    }


def public_sample_user_state(state):
    return {
        "user_id": state["user_id"],
        "rows": state["rows"],
        "history_items": state["history_items"],
        "history_in_previous_any_item": state["history_in_previous_any_item"],
        "history_in_previous_clicked_item": state["history_in_previous_clicked_item"],
        "history_not_in_previous_any_item": state["history_not_in_previous_any_item"],
        "target_in_history": state["target_in_history"],
        "unique_previous_any_items": len(state["previous_any_items"]),
        "unique_previous_clicked_items": len(state["previous_clicked_items"]),
    }


def probe_file(input_path, sample_user_limit=200, sample_user_mod=997, progress_interval=1_000_000):
    input_path = Path(input_path)
    started_at = time.time()

    total_rows = 0
    bad_width_rows = 0

    current_user = None
    current_user_seen_rows = set()
    current_user_pair_clicks = {}
    current_user_rows = 0
    current_sample_user = None

    seen_closed_users = set()
    user_block_lengths = []
    user_block_count = 0
    non_contiguous_user_count = 0
    non_contiguous_user_examples = []
    user_id_numeric_parse_failures = 0
    user_id_monotonic_violations = 0
    user_id_monotonic_examples = []
    previous_user_numeric = None

    exact_duplicate_rows_within_user_block = 0
    repeated_user_item_within_user_block = 0
    conflicting_user_item_click_within_user_block = 0
    repeated_user_item_examples = []
    conflicting_user_item_examples = []

    target_item_in_history_count = 0
    sampled_user_blocks = []
    sampled_history_totals = Counter()

    def finalize_user_block():
        nonlocal current_user, current_user_seen_rows, current_user_pair_clicks
        nonlocal current_user_rows, current_sample_user, user_block_count
        if current_user is None:
            return
        user_block_count += 1
        seen_closed_users.add(current_user)
        user_block_lengths.append(current_user_rows)
        if current_sample_user is not None:
            sampled_user_blocks.append(public_sample_user_state(current_sample_user))
            current_sample_user = None
        current_user_seen_rows = set()
        current_user_pair_clicks = {}
        current_user_rows = 0

    with input_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        columns = next(reader)
        column_indexes = {column: idx for idx, column in enumerate(columns)}
        expected_width = len(columns)
        required = ["user_id", "item_id", "click", *HISTORY_COLUMNS]
        missing_required = [column for column in required if column not in column_indexes]
        if missing_required:
            raise ValueError(f"Missing required columns: {', '.join(missing_required)}")

        for row in reader:
            if len(row) != expected_width:
                bad_width_rows += 1
                continue

            total_rows += 1
            user_id = row[column_indexes["user_id"]]
            item_id = row[column_indexes["item_id"]]
            click = row[column_indexes["click"]]

            if user_id != current_user:
                finalize_user_block()
                if user_id in seen_closed_users:
                    non_contiguous_user_count += 1
                    if len(non_contiguous_user_examples) < 10:
                        non_contiguous_user_examples.append(
                            {"user_id": user_id, "row_number": total_rows + 1}
                        )

                try:
                    user_numeric = int(user_id)
                except ValueError:
                    user_id_numeric_parse_failures += 1
                    user_numeric = None
                if (
                    user_numeric is not None
                    and previous_user_numeric is not None
                    and user_numeric < previous_user_numeric
                ):
                    user_id_monotonic_violations += 1
                    if len(user_id_monotonic_examples) < 10:
                        user_id_monotonic_examples.append(
                            {
                                "previous_user_id_numeric": previous_user_numeric,
                                "current_user_id": user_id,
                                "row_number": total_rows + 1,
                            }
                        )
                if user_numeric is not None:
                    previous_user_numeric = user_numeric

                current_user = user_id
                current_sample_user = (
                    make_sample_user_state(user_id)
                    if len(sampled_user_blocks) < sample_user_limit
                    and stable_int(user_id) % sample_user_mod == 0
                    else None
                )

            current_user_rows += 1
            row_tuple = tuple(row)
            if row_tuple in current_user_seen_rows:
                exact_duplicate_rows_within_user_block += 1
            else:
                current_user_seen_rows.add(row_tuple)

            pair = (user_id, item_id)
            previous_clicks = current_user_pair_clicks.get(pair)
            if previous_clicks is None:
                current_user_pair_clicks[pair] = {click}
            else:
                repeated_user_item_within_user_block += 1
                if len(repeated_user_item_examples) < 10:
                    repeated_user_item_examples.append(
                        {
                            "user_id": user_id,
                            "item_id": item_id,
                            "click": click,
                            "row_number": total_rows + 1,
                        }
                    )
                if click not in previous_clicks:
                    conflicting_user_item_click_within_user_block += 1
                    if len(conflicting_user_item_examples) < 10:
                        conflicting_user_item_examples.append(
                            {
                                "user_id": user_id,
                                "item_id": item_id,
                                "previous_click_values": sorted(previous_clicks),
                                "current_click": click,
                                "row_number": total_rows + 1,
                            }
                        )
                previous_clicks.add(click)

            history_values = [
                row[column_indexes[column]]
                for column in HISTORY_COLUMNS
                if row[column_indexes[column]] not in ("", "0")
            ]
            if item_id in history_values:
                target_item_in_history_count += 1
                if current_sample_user is not None:
                    current_sample_user["target_in_history"] += 1

            if current_sample_user is not None:
                current_sample_user["rows"] += 1
                previous_any = current_sample_user["previous_any_items"]
                previous_clicked = current_sample_user["previous_clicked_items"]
                for history_item in history_values:
                    current_sample_user["history_items"] += 1
                    sampled_history_totals["history_items"] += 1
                    if history_item in previous_any:
                        current_sample_user["history_in_previous_any_item"] += 1
                        sampled_history_totals["history_in_previous_any_item"] += 1
                    else:
                        current_sample_user["history_not_in_previous_any_item"] += 1
                        sampled_history_totals["history_not_in_previous_any_item"] += 1
                    if history_item in previous_clicked:
                        current_sample_user["history_in_previous_clicked_item"] += 1
                        sampled_history_totals["history_in_previous_clicked_item"] += 1
                previous_any.add(item_id)
                if click == "1":
                    previous_clicked.add(item_id)

            if progress_interval and total_rows % progress_interval == 0:
                elapsed = time.time() - started_at
                print(
                    f"processed_rows={total_rows:,} user_blocks={user_block_count:,} elapsed_seconds={elapsed:.1f}",
                    file=sys.stderr,
                    flush=True,
                )

    finalize_user_block()

    timestamp_columns = [
        column
        for column in columns
        if column.lower() in TIMESTAMP_COLUMN_CANDIDATES
    ]
    users_are_contiguous = non_contiguous_user_count == 0
    user_ids_monotonic = user_id_monotonic_violations == 0
    duplicate_scope = (
        "user block 内精确统计；本次探查确认 user 连续排列，因此对同一 user 内的重复 "
        "(user_id,item_id) 和完全重复行可视为全量精确统计。"
        if users_are_contiguous
        else "user block 内精确统计；由于发现 user 不连续，跨 block 重复未全量保存，不能视为全量精确去重结果。"
    )

    split_recommendations = [
        {
            "strategy": "timestamp-based split",
            "recommendation": "不建议",
            "reason": "字段中没有显式 timestamp，不能按真实时间戳切分。",
            "leakage_risk": "如果伪造 timestamp 口径，会导致实验不可审计。",
        },
        {
            "strategy": "user-level order-based split",
            "recommendation": "可作为 MVP 候选，但需要谨慎验证",
            "reason": "文件按 user_id 连续排列，且官方 Readme 说明 item 在 user level 按 click time 排序；但 ctr_data_1M.csv 是 task-specific 文件，history 构造仍未完全确认。",
            "leakage_risk": "如果 hist_1 到 hist_10 已使用 target 之后行为，仍会泄漏；当前 probe 不能完全排除。",
        },
        {
            "strategy": "user-block split",
            "recommendation": "适合做稳健性或冷启动式对照，不适合作为唯一 CTR MVP split",
            "reason": "user block 连续，按 user 分块容易实现且无同一 user 跨 split。",
            "leakage_risk": "评估更接近 unseen-user 泛化，不一定反映常规 ranking 场景；GAUC 对测试用户正负样本数量有要求。",
        },
        {
            "strategy": "official/random split baseline",
            "recommendation": "只适合复现官方 baseline 或对照",
            "reason": "官方 CTR benchmark 可能使用随机切分，但本项目规则默认不使用随机切分。",
            "leakage_risk": "同一 user/item 可能跨 train/test，且 history 字段可能放大泄漏风险。",
        },
    ]

    smoke_sample_recommendations = [
        {
            "name": "ctr_tiny_100k_head.csv",
            "purpose": "代码 smoke / debug，只验证 reader、feature parsing、batch shape 和最小 metric 流程。",
            "not_for": "不能当正式实验结果，head sample 有明显 user/order 偏置。",
        },
        {
            "name": "ctr_user_block_1m_seed20260525.csv",
            "purpose": "保留完整 user blocks 的约 1M 行样本，用于 dataloader、GAUC、order-based split 和 history 检查。",
            "not_for": "不能当 full validation/test；采样口径需要写入 data contract。",
        },
    ]

    elapsed_seconds = time.time() - started_at
    return {
        "file": {
            "path": str(input_path),
            "size_bytes": input_path.stat().st_size,
            "size_gib": round(input_path.stat().st_size / (1024 ** 3), 4),
            "columns": columns,
            "total_rows": total_rows,
            "bad_width_rows": bad_width_rows,
            "elapsed_seconds": round(elapsed_seconds, 3),
        },
        "user_order": {
            "user_block_count": user_block_count,
            "seen_closed_users": len(seen_closed_users),
            "users_are_contiguous": users_are_contiguous,
            "non_contiguous_user_count": non_contiguous_user_count,
            "non_contiguous_user_examples": non_contiguous_user_examples,
            "user_ids_monotonic": user_ids_monotonic,
            "user_id_monotonic_violations": user_id_monotonic_violations,
            "user_id_monotonic_examples": user_id_monotonic_examples,
            "user_id_numeric_parse_failures": user_id_numeric_parse_failures,
            "user_block_length_summary": summarize(user_block_lengths),
        },
        "duplicates_and_conflicts": {
            "scope": duplicate_scope,
            "exact_duplicate_rows_within_user_block": exact_duplicate_rows_within_user_block,
            "repeated_user_item_within_user_block": repeated_user_item_within_user_block,
            "conflicting_user_item_click_within_user_block": conflicting_user_item_click_within_user_block,
            "repeated_user_item_examples": repeated_user_item_examples,
            "conflicting_user_item_examples": conflicting_user_item_examples,
        },
        "history_probe": {
            "target_item_in_history_count": target_item_in_history_count,
            "target_item_in_history_rate": (
                round(target_item_in_history_count / total_rows, 8)
                if total_rows
                else None
            ),
            "sample_user_limit": sample_user_limit,
            "sample_user_mod": sample_user_mod,
            "sampled_user_blocks": len(sampled_user_blocks),
            "sampled_history_totals": dict(sampled_history_totals),
            "sampled_user_block_examples": sampled_user_blocks[:20],
            "interpretation": (
                "sampled history 检查只对比 ctr_data_1M.csv 文件内同一 user 之前出现过的 item；"
                "如果 history 不在此前行中，可能表示该 task-specific 文件没有保留完整原始历史，"
                "不能单独据此判定未来泄漏。"
            ),
        },
        "split_strategy": {
            "has_explicit_timestamp": bool(timestamp_columns),
            "timestamp_columns": timestamp_columns,
            "recommendations": split_recommendations,
        },
        "smoke_sample_strategy": smoke_sample_recommendations,
    }


def format_dict_inline(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def render_report(summary):
    user_order = summary["user_order"]
    dup = summary["duplicates_and_conflicts"]
    history = summary["history_probe"]
    split = summary["split_strategy"]
    lines = [
        "# ctr_data_1M.csv contract probe",
        "",
        "## 文件",
        "",
        f"- path: `{summary['file']['path']}`",
        f"- total rows: `{summary['file']['total_rows']:,}`",
        f"- bad width rows: `{summary['file']['bad_width_rows']:,}`",
        f"- elapsed seconds: `{summary['file']['elapsed_seconds']}`",
        "",
        "## 1. user 顺序检查",
        "",
        f"- user block count: `{user_order['user_block_count']:,}`",
        f"- users are contiguous: `{user_order['users_are_contiguous']}`",
        f"- non-contiguous user count: `{user_order['non_contiguous_user_count']:,}`",
        f"- user ids monotonic: `{user_order['user_ids_monotonic']}`",
        f"- user id monotonic violations: `{user_order['user_id_monotonic_violations']:,}`",
        f"- user block length summary: `{user_order['user_block_length_summary']}`",
        "",
        "## 2. 重复与冲突检查",
        "",
        f"- scope: {dup['scope']}",
        f"- exact duplicate rows within user block: `{dup['exact_duplicate_rows_within_user_block']:,}`",
        f"- repeated `(user_id,item_id)` within user block: `{dup['repeated_user_item_within_user_block']:,}`",
        f"- conflicting click for repeated `(user_id,item_id)` within user block: `{dup['conflicting_user_item_click_within_user_block']:,}`",
        "",
        "## 3. history 合理性检查",
        "",
        f"- target item in history count: `{history['target_item_in_history_count']:,}`",
        f"- target item in history rate: `{history['target_item_in_history_rate']}`",
        f"- sampled user blocks: `{history['sampled_user_blocks']}`",
        f"- sampled history totals: `{format_dict_inline(history['sampled_history_totals'])}`",
        f"- interpretation: {history['interpretation']}",
        "",
        "## 4. split 策略建议",
        "",
        f"- has explicit timestamp: `{split['has_explicit_timestamp']}`",
        f"- timestamp columns: `{split['timestamp_columns']}`",
    ]
    for item in split["recommendations"]:
        lines.extend(
            [
                "",
                f"### {item['strategy']}",
                "",
                f"- recommendation: {item['recommendation']}",
                f"- reason: {item['reason']}",
                f"- leakage risk: {item['leakage_risk']}",
            ]
        )

    lines.extend(["", "## 5. smoke sample 策略建议", ""])
    for item in summary["smoke_sample_strategy"]:
        lines.extend(
            [
                f"### {item['name']}",
                "",
                f"- purpose: {item['purpose']}",
                f"- not for: {item['not_for']}",
                "",
            ]
        )
    return "\n".join(lines)


def write_outputs(summary, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "ctr_data_1M_contract_probe.json"
    report_path = output_dir / "ctr_data_1M_contract_probe.md"
    with summary_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    report_path.write_text(render_report(summary), encoding="utf-8", newline="\n")
    return summary_path, report_path


def parse_args():
    parser = argparse.ArgumentParser(description="Probe Tenrec ctr_data_1M.csv data contract risks.")
    parser.add_argument("--input", required=True, help="Path to ctr_data_1M.csv")
    parser.add_argument("--output-dir", required=True, help="Directory for probe outputs")
    parser.add_argument("--sample-user-limit", type=int, default=200)
    parser.add_argument("--sample-user-mod", type=int, default=997)
    parser.add_argument("--progress-interval", type=int, default=1_000_000)
    return parser.parse_args()


def main():
    args = parse_args()
    summary = probe_file(
        args.input,
        sample_user_limit=args.sample_user_limit,
        sample_user_mod=args.sample_user_mod,
        progress_interval=args.progress_interval,
    )
    summary_path, report_path = write_outputs(summary, args.output_dir)
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
