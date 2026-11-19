import asyncio
import logging
import signal
import sys

import discord

from scripts.bot import bot
from scripts.config import TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


def _install_signals(loop: asyncio.AbstractEventLoop) -> None:
    """Close the bot cleanly on Ctrl+C and on the SIGTERM a container sends."""

    def shutdown() -> None:
        loop.create_task(bot.close())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:
            pass


def _run() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _install_signals(loop)

    try:
        loop.run_until_complete(bot.start(TOKEN))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(bot.close())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


if not TOKEN:
    sys.exit("DISCORD_TOKEN is missing. Copy .env.example to .env and fill it in.")

try:
    _run()
except discord.PrivilegedIntentsRequired:
    sys.exit(
        "Message Content Intent is disabled for this application.\n"
        "Open https://discord.com/developers/applications -> your app -> Bot ->\n"
        "Privileged Gateway Intents, enable Message Content, then restart."
    )
except discord.LoginFailure:
    sys.exit("Discord rejected the token. Check DISCORD_TOKEN in .env.")
except KeyboardInterrupt:
    sys.exit(130)
