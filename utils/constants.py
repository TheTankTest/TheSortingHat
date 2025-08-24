from typing import Dict, List, Tuple, Optional
import json
from functools import lru_cache
from config import BOSS_POINTS_PATH

# Hiscore module mapping
HISCORE_MODULE = {
    "normal": None,
    "ironman": "ironman",
    "hardcore_ironman": "hardcore_ironman",
    "ultimate": "ultimate",
    "group_ironman": "group_ironman",
    "unranked_group_ironman": "unranked_group_ironman",
}

# Canonical account type dropdown options
ACCOUNT_TYPE_OPTIONS: List[Tuple[str, str, str]] = [
    ("normal", "Normal", "Standard account"),
    ("ironman", "Ironman", "Ironman hiscores"),
    ("hardcore_ironman", "Hardcore Ironman", "HCIM hiscores"),
    ("ultimate", "Ultimate Ironman", "UIM hiscores"),
    ("group_ironman", "Group Ironman", "GIM hiscores"),
    ("unranked_group_ironman", "Unranked Group Ironman", "UGIM hiscores"),
]

# Input aliases → canonical key
ACCOUNT_TYPE_ALIASES = {
    "main": "normal",
    "normal": "normal",
    "std": "normal",
    "iron": "ironman",
    "ironman": "ironman",
    "im": "ironman",
    "hardcore": "hardcore_ironman",
    "hardcore ironman": "hardcore_ironman",
    "hcim": "hardcore_ironman",
    "hc": "hardcore_ironman",
    "ultimate": "ultimate",
    "ultimate ironman": "ultimate",
    "uim": "ultimate",
    "ui": "ultimate",
    "group": "group_ironman",
    "gim": "group_ironman",
    "unranked group": "unranked_group_ironman",
    "ugim": "unranked_group_ironman",
    "ugi": "unranked_group_ironman",
}

def normalize_account_type(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    key = s.strip().lower()
    return ACCOUNT_TYPE_ALIASES.get(key, key if key in HISCORE_MODULE else None)

# index_lite tail order → bosses
API_BOSS_ORDER: List[str] = [
    "Abyssal Sire","Alchemical Hydra","Amoxliatl","Araxxor","Artio","Barrows Chests","Bryophyta","Callisto",
    "Calvar'ion","Cerberus","Chambers Of Xeric","Chambers Of Xeric (CM)","Chaos Elemental",
    "Chaos Fanatic","Commander Zilyana","Corporeal Beast","Crazy Archaeologist","Dagannoth Prime",
    "Dagannoth Rex","Dagannoth Supreme","Deranged Archaeologist","Doom of Mokhaiotl","Duke Sucellus","General Graardor",
    "Giant Mole","Grotesque Guardians","Hespori","Kalphite Queen","King Black Dragon","Kraken",
    "Kree'Arra","K'ril Tsutsaroth","Lunar Chests","Mimic","Nex","Nightmare","Phosani's Nightmare",
    "Obor","Phantom Muspah","Sarachnis","Scorpia","Scurrius","Skotizo","Sol Heredit","Spindel","Tempoross",
    "The Gauntlet","The Corrupted Gauntlet","The Hueycoatl","The Leviathan","The Royal Titans",
    "The Whisperer","Theatre Of Blood","Theatre Of Blood (HM)","Thermonuclear Smoke Devil",
    "Tombs of Amascut","Tombs of Amascut (Expert Mode)","TzKal-Zuk","TzTok-Jad","Vardorvis",
    "Venenatis","Vet'ion","Vorkath","Wintertodt","Yama","Zalcano","Zulrah"
]

@lru_cache(maxsize=1)
def get_boss_points() -> Dict[str, float]:
    with open(BOSS_POINTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
