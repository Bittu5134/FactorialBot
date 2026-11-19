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

log = logging.getLogger("factorialbot")

CLOSE_TIMEOUT_SECS = 10


async def _shutdown() -> None:
    try:
        await asyncio.wait_for(bot.close(), CLOSE_TIMEOUT_SECS)
    except Exception:
        log.warning("Clean shutdown timed out", exc_info=True)


def _run() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(bot.start(TOKEN), name="factorialbot:start")

    def on_signal() -> None:
        log.info("Shutting down")
        task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, on_signal)
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(task)
    except asyncio.CancelledError:
        pass

    try:
        loop.run_until_complete(_shutdown())
    finally:
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
