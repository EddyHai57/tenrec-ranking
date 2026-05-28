import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class GaucResult:
    gauc: float | None
    valid_user_count: int
    only_positive_user_count: int
    only_negative_user_count: int
    total_user_count: int
    valid_row_count: int
    total_row_count: int
    row_coverage_rate: float | None


def binary_auc(y_true: Iterable[int], y_score: Iterable[float]) -> float:
    labels = [int(value) for value in y_true]
    scores = [float(value) for value in y_score]
    if len(labels) != len(scores):
        raise ValueError("y_true and y_score must have the same length")
    pos_count = sum(labels)
    neg_count = len(labels) - pos_count
    if pos_count == 0 or neg_count == 0:
        raise ValueError("AUC is undefined when y_true has a single class")

    order = sorted(range(len(scores)), key=lambda idx: scores[idx])
    ranks = [0.0] * len(scores)
    current = 0
    while current < len(order):
        end = current + 1
        while end < len(order) and scores[order[end]] == scores[order[current]]:
            end += 1
        average_rank = (current + 1 + end) / 2.0
        for idx in order[current:end]:
            ranks[idx] = average_rank
        current = end

    pos_rank_sum = sum(rank for rank, label in zip(ranks, labels) if label == 1)
    return (pos_rank_sum - pos_count * (pos_count + 1) / 2.0) / (pos_count * neg_count)


def binary_log_loss(y_true: Iterable[int], y_score: Iterable[float], eps: float = 1e-15) -> float:
    labels = [int(value) for value in y_true]
    scores = [float(value) for value in y_score]
    if len(labels) != len(scores):
        raise ValueError("y_true and y_score must have the same length")
    if not labels:
        raise ValueError("log loss is undefined for empty inputs")
    total = 0.0
    for label, score in zip(labels, scores):
        clipped = min(max(score, eps), 1.0 - eps)
        total += label * math.log(clipped) + (1 - label) * math.log(1.0 - clipped)
    return -total / len(labels)


def pcoc(y_true: Iterable[int], y_score: Iterable[float]) -> float:
    labels = [int(value) for value in y_true]
    scores = [float(value) for value in y_score]
    if len(labels) != len(scores):
        raise ValueError("y_true and y_score must have the same length")
    if not labels:
        raise ValueError("PCOC is undefined for empty inputs")
    actual_ctr = sum(labels) / len(labels)
    if actual_ctr <= 0:
        raise ValueError("PCOC is undefined when mean(y_true) is zero")
    return (sum(scores) / len(scores)) / actual_ctr


def impression_weighted_gauc(
    y_true: Iterable[int],
    y_score: Iterable[float],
    groups: Iterable[int | str],
) -> GaucResult:
    labels = [int(value) for value in y_true]
    scores = [float(value) for value in y_score]
    group_values = [value for value in groups]
    if not (len(labels) == len(scores) == len(group_values)):
        raise ValueError("y_true, y_score and groups must have the same length")

    grouped: dict[int | str, dict[str, list]] = defaultdict(lambda: {"y": [], "s": []})
    for label, score, group in zip(labels, scores, group_values):
        grouped[group]["y"].append(label)
        grouped[group]["s"].append(score)

    weighted_auc_sum = 0.0
    valid_row_count = 0
    only_positive_user_count = 0
    only_negative_user_count = 0

    for state in grouped.values():
        user_labels = state["y"]
        has_positive = any(label == 1 for label in user_labels)
        has_negative = any(label == 0 for label in user_labels)
        if not (has_positive and has_negative):
            if has_positive:
                only_positive_user_count += 1
            else:
                only_negative_user_count += 1
            continue
        user_auc = binary_auc(user_labels, state["s"])
        weight = len(user_labels)
        weighted_auc_sum += user_auc * weight
        valid_row_count += weight

    total_row_count = len(labels)
    row_coverage_rate = (
        valid_row_count / total_row_count if total_row_count else None
    )
    gauc_value = weighted_auc_sum / valid_row_count if valid_row_count else None
    return GaucResult(
        gauc=gauc_value,
        valid_user_count=sum(
            1
            for state in grouped.values()
            if any(label == 1 for label in state["y"])
            and any(label == 0 for label in state["y"])
        ),
        only_positive_user_count=only_positive_user_count,
        only_negative_user_count=only_negative_user_count,
        total_user_count=len(grouped),
        valid_row_count=valid_row_count,
        total_row_count=total_row_count,
        row_coverage_rate=row_coverage_rate,
    )
