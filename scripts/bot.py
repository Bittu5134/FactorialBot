import asyncio
import hashlib
import json
import logging
import random

import aiohttp
import discord
from discord import app_commands

from . import config, db, replies, utils
from .factorials import Factorial, find_factorals
from .ui import HelpView, SettingsView, support_embed

log = logging.getLogger(__name__)

intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True
intents.dm_messages = True
intents.message_content = True


class FactorialBot(discord.Client):
    async def close(self) -> None:
        await db.close_db(utils.db_conn)
        utils.db_conn = None
        await super().close()


bot = FactorialBot(intents=intents)
tree = app_commands.CommandTree(bot)

ERROR_TEXT = "Something broke on my end. Try again in a moment."


async def _on_tree_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    log.error(
        "Command %s failed: %s",
        getattr(interaction.command, "name", "unknown"),
        error,
        exc_info=error,
    )
    if interaction.response.is_done():
        send = interaction.followup.send
    else:
        send = interaction.response.send_message
    try:
        await send(ERROR_TEXT, ephemeral=True)
    except discord.HTTPException:
        log.warning("Could not report a command error", exc_info=True)


tree.on_error = _on_tree_error


def _promo_due() -> bool:
    return random.random() < config.SUPPORT_CHANCE


@tree.command(name="factorial", description="Get one factorial, with attitude")
async def factorial_command(interaction: discord.Interaction, number: int) -> None:
    if not utils.reply_allowed(interaction.channel_id or 0):
        await interaction.response.send_message(
            "Give the last one a second to land.", ephemeral=True
        )
        return

    if number < 0:
        answer = replies.refuse_negative(number)
    elif number > config.MAX_N:
        answer = replies.refuse(number)
    else:
        answer = replies.compose(Factorial(number))

    payload: dict = {
        "content": answer.text,
        "silent": True,
        "allowed_mentions": discord.AllowedMentions.none(),
    }
    if _promo_due():
        payload["embed"] = support_embed()

    await interaction.response.send_message(**payload)


@tree.command(name="setting", description="Pick the channels the bot may answer in")
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
async def setting_command(interaction: discord.Interaction) -> None:
    allowed = sorted(utils.allowed.get(interaction.guild_id, set()))
    await interaction.response.send_message(
        view=SettingsView(interaction.guild, allowed),
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )


@tree.command(name="help", description="What is this bot and why is it here")
async def help_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        view=HelpView(bot.user.id if bot.user else None),
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )


SYNC_TIMEOUT_SECS = 30


def _commands_fingerprint() -> str:
    payload = [command.to_dict(tree) for command in tree.get_commands()]
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


async def _sync_if_changed() -> int:
    """Sync only when the command set actually changed."""
    fingerprint = _commands_fingerprint()
    key = f"commands:{config.GUILD_ID or 0}"

    stored = (
        await db.get_meta(utils.db_conn, key) if utils.db_conn is not None else None
    )
    if stored == fingerprint:
        log.info("Slash commands unchanged; sync skipped")
        return 0

    if config.GUILD_ID:
        guild = discord.Object(id=config.GUILD_ID)
        tree.copy_global_to(guild=guild)
        synced = await tree.sync(guild=guild)
    else:
        synced = await tree.sync()
    if utils.db_conn is not None:
        await db.set_meta(utils.db_conn, key, fingerprint)
    return len(synced)


@bot.event
async def setup_hook():
    try:
        utils.db_conn = await db.open_db(config.DB_PATH)
        utils.allowed = await db.load_allowed(utils.db_conn)
    except Exception:
        utils.db_conn = None
        utils.allowed = {}
        log.exception("Settings database unavailable; running with defaults")

    try:
        synced = await asyncio.wait_for(_sync_if_changed(), SYNC_TIMEOUT_SECS)
        if synced:
            log.info("Synced %d slash command(s).", synced)
    except Exception as exc:
        log.warning(
            "Command sync skipped (%s); the registered commands are still live", exc
        )
        log.debug("Command sync failure", exc_info=True)

    log.info(
        "%d guild(s) have a channel whitelist; promo %.2f",
        len(utils.allowed),
        config.SUPPORT_CHANCE,
    )


@bot.event
async def on_ready():
    log.info("Logged in as %s in %d guild(s)", bot.user, len(bot.guilds))


@bot.event
async def on_resumed() -> None:
    log.info("Reconnected to Discord")


@bot.event
async def on_disconnect() -> None:
    if bot.is_closed():
        return
    log.warning("Disconnected from Discord, reconnecting")


async def _post_log(content: str) -> None:
    """Send one line to LOG_WEBHOOK_URL when it is configured."""
    if not config.LOG_WEBHOOK_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(config.LOG_WEBHOOK_URL, session=session)
            await webhook.send(
                content=content,
                username="FactorialBot Logs",
                allowed_mentions=discord.AllowedMentions.none(),
            )
    except Exception:
        log.warning("Could not post guild log", exc_info=True)


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    log.info(
        "Joined guild %s (%s) with %s members",
        guild.name,
        guild.id,
        guild.member_count,
    )
    await _post_log(
        f"➕ **Joined** {guild.name} (`{guild.id}`) · "
        f"{guild.member_count} members · {len(bot.guilds)} guilds total"
    )


@bot.event
async def on_guild_remove(guild: discord.Guild) -> None:
    log.info("Removed from guild %s (%s)", guild.name, guild.id)
    await _post_log(
        f"➖ **Removed** {guild.name} (`{guild.id}`) · {len(bot.guilds)} guilds total"
    )


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or message.webhook_id:
        return

    if message.guild:
        allowed = utils.allowed.get(message.guild.id)
        if allowed:
            parent_id = getattr(message.channel, "parent_id", None)
            if message.channel.id not in allowed and parent_id not in allowed:
                return
        me = message.guild.me
        if me and not message.channel.permissions_for(me).send_messages:
            return

    found = find_factorals(message.content or "")
    if not found:
        return

    if not utils.reply_allowed(message.channel.id):
        return

    answer = replies.compose(
        found[0],
        extra=replies.too_many(found[1:]) if len(found) > 1 else "",
    )

    payload: dict = {
        "mention_author": False,
        "silent": True,
        "allowed_mentions": discord.AllowedMentions.none(),
        "content": answer.text,
    }
    if _promo_due():
        payload["embed"] = support_embed()

    try:
        await message.reply(**payload)
    except discord.HTTPException:
        log.warning("Could not reply in channel %s", message.channel.id, exc_info=True)
