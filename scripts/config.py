import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: str | Path = BASE_DIR / ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


_load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "")

# Development only: sync commands to this guild instead of globally.
GUILD_ID = os.getenv("GUILD_ID")
GUILD_ID = int(GUILD_ID) if GUILD_ID else None

DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "factorialbot.db"))

LOG_WEBHOOK_URL = os.getenv("LOG_WEBHOOK_URL", "")

PATREON_URL = "https://www.patreon.com/c/LazyBittu"

SUPPORT_CHANCE = float(os.getenv("SUPPORT_CHANCE", "0.1"))

# View Channels, Send Messages, Read Message History.
INVITE_PERMISSIONS = 68608

REPLY_COOLDOWN_SECS = 1
MAX_EXTRA_MENTIONS = 2

# Discord caps a single select at 25 choices; the stored list has no limit.
MAX_PICKER_CHOICES = 25

# Up to this n the answer is typed out in full.
EXACT_MAX_N = 22

MANTISSA_DIGITS = 4

MAX_INPUT_DIGITS = 15

MAX_N = 10**15

DEFAULT_FOOTER = ""
