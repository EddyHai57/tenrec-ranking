import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


SPLITS = ["train", "valid", "test"]
REQUIRED_COLUMNS = [
    "user_id",
    "item_id",
    "click",
    "follow",
    "like",
    "share",
    "video_category",
    "gender",
    "age",
]


def empty_split_stats():
    return {
        "row_count": 0,
        "users": set(),
        "items": set(),
        "click": Counter(),
        "follow_1": 0,
        "like_1": 0,
        "share_1": 0,
        "video_category": Counter(),
        "gender": Counter(),
        "age": Counter(),
        "missing_video_category": 0,
    }


def split_indices(row_count):
    if row_count < 3:
        return ["train"] * row_count
    valid_count = max(1, int(row_count * 0.1))
    test_count = max(1, int(row_count * 0.1))
    train_count = row_count - valid_count - test_count
    if train_count < 1:
        train_count = 1
        overflow = train_count + valid_count + test_count - row_count
        if test_count >= valid_count and test_count > 1:
            test_count -= overflow
        elif valid_count > 1:
            valid_count -= overflow
    return ["train"] * train_count + ["valid"] * valid_count + ["test"] * test_count


def rate(numerator, denominator):
    if denominator == 0:
        return None
    return round(numerator / denominator, 8)


def top_dict(counter, limit=10):
    return dict(counter.most_common(limit))


def public_split_stats(stats):
    click_1 = stats["click"].get("1", 0)
    return {
        "row_count": stats["row_count"],
        "user_count": len(stats["users"]),
        "item_count": len(stats["items"]),
        "click": dict(stats["click"]),
        "click_positive_rate": rate(click_1, stats["row_count"]),
        "follow_1": stats["follow_1"],
        "like_1": stats["like_1"],
        "share_1": stats["share_1"],
        "video_category_top": top_dict(stats["video_category"]),
        "gender": dict(stats["gender"]),
        "age": dict(stats["age"]),
        "missing_video_category": stats["missing_video_category"],
    }


def update_split_stats(stats, row, indexes):
    stats["row_count"] += 1
    stats["users"].add(row[indexes["user_id"]])
    stats["items"].add(row[indexes["item_id"]])
    stats["click"][row[indexes["click"]]] += 1
    if row[indexes["follow"]] == "1":
        stats["follow_1"] += 1
    if row[indexes["like"]] == "1":
        stats["like_1"] += 1
    if row[indexes["share"]] == "1":
        stats["share_1"] += 1
    video_category = row[indexes["video_category"]]
    stats["video_category"][video_category] += 1
    if video_category in ("", "\\N"):
        stats["missing_video_category"] += 1
    stats["gender"][row[indexes["gender"]]] += 1
    stats["age"][row[indexes["age"]]] += 1


def empty_gauc_user_state():
    return {"rows": 0, "click": Counter()}


def update_gauc_user_state(gauc_states, split, user_id, click):
    state = gauc_states[split][user_id]
    state["rows"] += 1
    state["click"][click] += 1


def summarize_gauc(gauc_states):
    result = {}
    for split in ["valid", "test"]:
        states = gauc_states[split]
        valid_users = 0
        only_positive_users = 0
        only_negative_users = 0
        rows_lt_2_users = 0
        valid_rows = 0
        total_rows = 0
        for state in states.values():
            rows = state["rows"]
            total_rows += rows
            has_pos = state["click"].get("1", 0) > 0
            has_neg = state["click"].get("0", 0) > 0
            if rows < 2:
                rows_lt_2_users += 1
            if has_pos and has_neg:
                valid_users += 1
                valid_rows += rows
            elif has_pos:
                only_positive_users += 1
            elif has_neg:
                only_negative_users += 1
        result[split] = {
            "total_user_count": len(states),
            "valid_gauc_user_count": valid_users,
            "only_positive_user_count": only_positive_users,
            "only_negative_user_count": only_negative_users,
            "rows_lt_2_user_count": rows_lt_2_users,
            "valid_gauc_row_count": valid_rows,
            "valid_gauc_row_coverage_rate": rate(valid_rows, total_rows),
        }
    return result


def process_user_block(rows, indexes, split_stats, gauc_states, short_user_counts):
    assignments = split_indices(len(rows))
    short_user_counts[str(len(rows)) if len(rows) < 3 else ">=3"] += 1
    for row, split in zip(rows, assignments):
        update_split_stats(split_stats[split], row, indexes)
        if split in ("valid", "test"):
            update_gauc_user_state(
                gauc_states,
                split,
                row[indexes["user_id"]],
                row[indexes["click"]],
            )


def inspect_split_feasibility(input_path):
    input_path = Path(input_path)
    split_stats = {split: empty_split_stats() for split in SPLITS}
    gauc_states = {split: defaultdict(empty_gauc_user_state) for split in ("valid", "test")}
    short_user_counts = Counter()
    total_rows = 0
    user_block_count = 0
    current_user = None
    current_rows = []

    with input_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        indexes = {column: idx for idx, column in enumerate(header)}
        missing = [column for column in REQUIRED_COLUMNS if column not in indexes]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        def flush_current():
            nonlocal user_block_count, current_rows
            if not current_rows:
                return
            user_block_count += 1
            process_user_block(current_rows, indexes, split_stats, gauc_states, short_user_counts)
            current_rows = []

        for row in reader:
            total_rows += 1
            user_id = row[indexes["user_id"]]
            if current_user is None:
                current_user = user_id
            if user_id != current_user:
                flush_current()
                current_user = user_id
            current_rows.append(row)
        flush_current()

    public_stats = {split: public_split_stats(split_stats[split]) for split in SPLITS}
    train_items = split_stats["train"]["items"]
    valid_items = split_stats["valid"]["items"]
    test_items = split_stats["test"]["items"]
    valid_unseen_train = valid_items - train_items
    test_unseen_train = test_items - train_items
    test_unseen_train_valid = test_items - (train_items | valid_items)
    gauc = summarize_gauc(gauc_states)

    return {
        "input_path": str(input_path),
        "split_rule": {
            "description": "每个 user 内按文件顺序切分；rows < 3 全部 train；rows >= 3 时 train/valid/test = 80/10/10，valid/test 至少各 1 行；不打乱、不去重。",
            "shuffle": False,
            "deduplicate": False,
            "preserve_row_order": True,
            "short_user_assignment": "user rows < 3 -> train only",
            "short_user_counts": dict(short_user_counts),
        },
        "source": {
            "total_rows": total_rows,
            "user_block_count": user_block_count,
        },
        "splits": public_stats,
        "gauc_feasibility": gauc,
        "cold_item": {
            "valid_unseen_train_item_count": len(valid_unseen_train),
            "valid_unseen_train_item_rate": rate(len(valid_unseen_train), len(valid_items)),
            "test_unseen_train_item_count": len(test_unseen_train),
            "test_unseen_train_item_rate": rate(len(test_unseen_train), len(test_items)),
            "test_unseen_train_valid_item_count": len(test_unseen_train_valid),
            "test_unseen_train_valid_item_rate": rate(len(test_unseen_train_valid), len(test_items)),
        },
        "feature_recommendation": {
            "first_stage_features": ["user_id", "item_id", "video_category", "gender", "age"],
            "hold_out_features": ["watching_times", "hist_1...hist_10", "follow", "like", "share"],
            "reason": {
                "watching_times": "可能是 post-exposure / post-click 行为，有 leakage 风险。",
                "hist": "构造口径未完全验证，暂不作为第一版 click baseline 输入。",
                "follow_like_share": "是多任务标签，不应作为 click baseline 输入特征，除非明确做多任务或 label leakage 对照。",
            },
        },
        "conclusion": build_conclusion(gauc, public_stats),
    }


def build_conclusion(gauc, public_stats):
    valid_coverage = gauc["valid"]["valid_gauc_row_coverage_rate"] or 0
    test_coverage = gauc["test"]["valid_gauc_row_coverage_rate"] or 0
    enough_for_smoke = (
        public_stats["train"]["row_count"] > 0
        and public_stats["valid"]["row_count"] > 0
        and public_stats["test"]["row_count"] > 0
        and valid_coverage > 0.5
        and test_coverage > 0.5
    )
    return {
        "suitable_for_dataloader_smoke": True,
        "suitable_for_tiny_lr_mlp_overfit_test": enough_for_smoke,
        "suitable_for_formal_metrics": False,
        "can_start_minimal_src_configs_design": enough_for_smoke,
        "summary": (
            "该 user-block smoke sample 足够支持 dataloader、split 和 GAUC smoke；"
            "可以进入最小 src/configs 设计，但正式指标仍必须在 full run 或更严格数据契约确认后报告。"
            if enough_for_smoke
            else "该 user-block smoke sample 可用于 dataloader smoke，但 GAUC 覆盖不足；进入 tiny baseline 前应调整 sample 或 split。"
        ),
    }


def render_split_table(split_name, stats):
    lines = [
        f"### {split_name}",
        "",
        f"- row count: `{stats['row_count']:,}`",
        f"- user count: `{stats['user_count']:,}`",
        f"- item count: `{stats['item_count']:,}`",
        f"- click: `{stats['click']}`",
        f"- click positive rate: `{stats['click_positive_rate']}`",
        f"- follow=1: `{stats['follow_1']:,}`",
        f"- like=1: `{stats['like_1']:,}`",
        f"- share=1: `{stats['share_1']:,}`",
        f"- video_category top: `{stats['video_category_top']}`",
        f"- gender: `{stats['gender']}`",
        f"- age: `{stats['age']}`",
        f"- missing video_category: `{stats['missing_video_category']:,}`",
        "",
    ]
    return lines


def render_report(summary):
    lines = [
        "# ctr_user_block_1m split feasibility",
        "",
        "## 输入与规则",
        "",
        f"- input: `{summary['input_path']}`",
        f"- total rows: `{summary['source']['total_rows']:,}`",
        f"- user blocks: `{summary['source']['user_block_count']:,}`",
        f"- split rule: {summary['split_rule']['description']}",
        f"- short user counts: `{summary['split_rule']['short_user_counts']}`",
        "",
        "## split 基础统计",
        "",
    ]
    for split in SPLITS:
        lines.extend(render_split_table(split, summary["splits"][split]))

    lines.extend(["## GAUC 可行性", ""])
    for split in ("valid", "test"):
        stats = summary["gauc_feasibility"][split]
        lines.extend(
            [
                f"### {split}",
                "",
                f"- total user count: `{stats['total_user_count']:,}`",
                f"- valid GAUC user count: `{stats['valid_gauc_user_count']:,}`",
                f"- only positive user count: `{stats['only_positive_user_count']:,}`",
                f"- only negative user count: `{stats['only_negative_user_count']:,}`",
                f"- rows < 2 user count: `{stats['rows_lt_2_user_count']:,}`",
                f"- valid GAUC row count: `{stats['valid_gauc_row_count']:,}`",
                f"- valid GAUC row coverage rate: `{stats['valid_gauc_row_coverage_rate']}`",
                "",
            ]
        )

    cold = summary["cold_item"]
    lines.extend(
        [
            "## cold item / unseen item",
            "",
            f"- valid items unseen in train: `{cold['valid_unseen_train_item_count']:,}` / rate `{cold['valid_unseen_train_item_rate']}`",
            f"- test items unseen in train: `{cold['test_unseen_train_item_count']:,}` / rate `{cold['test_unseen_train_item_rate']}`",
            f"- test items unseen in train+valid: `{cold['test_unseen_train_valid_item_count']:,}` / rate `{cold['test_unseen_train_valid_item_rate']}`",
            "",
            "## feature 使用建议",
            "",
            f"- 第一阶段可用: `{summary['feature_recommendation']['first_stage_features']}`",
            f"- 暂时不要用: `{summary['feature_recommendation']['hold_out_features']}`",
            "- 原因：`watching_times` 可能有 post-exposure / post-click leakage；`hist_*` 构造口径未完全验证；`follow/like/share` 是多任务标签。",
            "",
            "## 结论",
            "",
            f"- suitable for dataloader smoke: `{summary['conclusion']['suitable_for_dataloader_smoke']}`",
            f"- suitable for tiny LR/MLP overfit test: `{summary['conclusion']['suitable_for_tiny_lr_mlp_overfit_test']}`",
            f"- suitable for formal metrics: `{summary['conclusion']['suitable_for_formal_metrics']}`",
            f"- can start minimal src/configs design: `{summary['conclusion']['can_start_minimal_src_configs_design']}`",
            f"- summary: {summary['conclusion']['summary']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(summary, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "ctr_user_block_1m_split_feasibility.json"
    md_path = output_dir / "ctr_user_block_1m_split_feasibility.md"
    with json_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    md_path.write_text(render_report(summary), encoding="utf-8", newline="\n")
    return json_path, md_path


def parse_args():
    parser = argparse.ArgumentParser(description="Check CTR user-block sample split feasibility.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    summary = inspect_split_feasibility(args.input)
    json_path, md_path = write_outputs(summary, args.output_dir)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
