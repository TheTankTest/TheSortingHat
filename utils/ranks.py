from typing import List, Tuple

RANK_THRESHOLDS: List[Tuple[int, str]] = [
    (500_000, "Zenyte"),
    (250_000, "Onyx"),
    (100_000, "Dragon"),
    (50_000, "Rune"),
    (25_000, "Adamant"),
    (10_000, "Mithril"),
    (5_000, "Gold"),
    (2_500, "Steel"),
    (1_000, "Iron"),
    (0, "Bronze"),
]

def get_rank_name(points: float) -> str:
    for threshold, name in RANK_THRESHOLDS:
        if points >= threshold:
            return name
    return "Bronze"
