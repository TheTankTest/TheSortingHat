import os
from dotenv import load_dotenv

load_dotenv()

# Core
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in .env")

# IDs (make optional but recommended)
GUILD_ID = int(os.getenv("GUILD_ID", "0")) or None
STAFF_CHANNEL_ID = int(os.getenv("STAFF_CHANNEL_ID", "0")) or None
MEMBER_ROLE_ID = int(os.getenv("MEMBER_ROLE_ID", "0")) or None
VISITOR_ROLE_ID = int(os.getenv("VISITOR_ROLE_ID", "0")) or None
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", "0")) or None

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
BOSS_POINTS_PATH = os.path.join(DATA_DIR, "boss_points.json")

# Misc
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes", "on")
