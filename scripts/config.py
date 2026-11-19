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
            # .env wins over the ambient environment so the repo config is the truth.
            os.environ[k.strip()] = v.strip().strip("'\"")


_load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "")

LOG_WEBHOOK_URL = os.getenv("LOG_WEBHOOK_URL", "")

# Set to a guild id while developing to sync commands there instantly.
GUILD_ID: int | None = None

DB_PATH = BASE_DIR / "factorialbot.db"

PATREON_URL = "https://www.patreon.com/c/LazyBittu"

# Fraction of answers that carry the Patreon embed. 0 turns the plug off.
SUPPORT_CHANCE = 0.1

# View Channels, Send Messages, Read Message History.
INVITE_PERMISSIONS = 68608

# Minimum gap between two replies in the same channel.
REPLY_COOLDOWN_SECS = 3

# Factorials named in the "one at a time, please" footnote.
MAX_EXTRA_MENTIONS = 2

# Discord caps a select at 25 choices; nothing else is limited.
MAX_PICKER_CHOICES = 25

# Up to this n the answer is typed out in full.
EXACT_MAX_N = 22

MANTISSA_DIGITS = 4

MAX_INPUT_DIGITS = 15

MAX_N = 10**15

DEFAULT_FOOTER = "/factorial • accuracy not guaranteed"
