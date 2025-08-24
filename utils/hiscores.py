import csv
import io
from typing import Dict, List, Tuple
import aiohttp

from utils.constants import HISCORE_MODULE, API_BOSS_ORDER

def build_base_url(account_type: str) -> str:
    suffix = HISCORE_MODULE.get(account_type)
    return f"https://secure.runescape.com/m=hiscore_oldschool_{suffix}" if suffix else \
           "https://secure.runescape.com/m=hiscore_oldschool"

async def fetch_csv_rows(player: str, account_type: str) -> List[List[int]]:
    base = build_base_url(account_type)
    url = f"{base}/index_lite.ws?player={player}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=20) as resp:
            if resp.status == 404:
                return []
            resp.raise_for_status()
            text = await resp.text()

    rows: List[List[int]] = []
    for row in csv.reader(io.StringIO(text)):
        try:
            parsed = [int(x) if x != "-1" else -1 for x in row]
        except Exception:
            parsed = [-1] * len(row)
        rows.append(parsed)
    return rows

def extract_boss_kc(rows: List[List[int]]) -> Dict[str, int]:
    if not rows:
        return {}
    tail_len = len(API_BOSS_ORDER)
    start = max(0, len(rows) - tail_len)
    relevant = rows[start : start + tail_len]
    kc_map: Dict[str, int] = {}
    for name, line in zip(API_BOSS_ORDER, relevant):
        kc = line[1] if len(line) > 1 and line[1] >= 0 else 0
        kc_map[name] = kc
    return kc_map

def compute_points(kc_map: Dict[str, int], boss_points: Dict[str, float]) -> Tuple[float, List[Tuple[str, int, float]]]:
    total = 0.0
    breakdown: List[Tuple[str, int, float]] = []
    for boss, kc in kc_map.items():
        if kc > 0 and boss in boss_points:
            pts = boss_points[boss] * kc
            total += pts
            breakdown.append((boss, kc, pts))
    breakdown.sort(key=lambda x: x[2], reverse=True)
    return total, breakdown
