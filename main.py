import logging
import sys

import discord

from scripts.bot import bot
from scripts.config import TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)

if not TOKEN:
    sys.exit("DISCORD_TOKEN is missing. Copy .env.example to .env and fill it in.")

try:
    bot.run(TOKEN)
except discord.PrivilegedIntentsRequired:
    sys.exit(
        "Message Content Intent is disabled for this application.\n"
        "Open https://discord.com/developers/applications -> your app -> Bot ->\n"
        "Privileged Gateway Intents, enable Message Content, then restart."
    )
except discord.LoginFailure:
    sys.exit("Discord rejected the token. Check DISCORD_TOKEN in .env.")
