import logging
import random

import aiohttp
import discord
from discord import app_commands

from . import config, db, replies, utils
from .factorials import Factorial, find_factorals
from .ui import (
    FactHelpView,
    FactReplyView,
    FactStatsView,
    SettingsView,
    support_embed,
)

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

    if _promo_due():
        await interaction.response.send_message(
            content=answer.text,
            embed=support_embed(),
            silent=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return

    await interaction.response.send_message(
        view=FactReplyView(answer),
        silent=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )


@tree.command(
    name="factstats", description="See how many factorials this server has produced"
)
@app_commands.guild_only()
async def factstats_command(interaction: discord.Interaction) -> None:
    if utils.db_conn is None:
        await interaction.response.send_message(
            "The stats database is not ready yet. Try again in a moment.",
            ephemeral=True,
        )
        return

    await interaction.response.defer()
    stats = await db.get_guild_stats(utils.db_conn, interaction.guild_id)
    rows = await db.top(utils.db_conn, interaction.guild_id, 5)
    await interaction.followup.send(
        view=FactStatsView(stats, rows),
        silent=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )


@tree.command(
    name="setting", description="Pick up to 5 channels for FactorialBot to track"
)
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
async def setting_command(interaction: discord.Interaction) -> None:
    tracked = sorted(utils.tracked.get(interaction.guild_id, set()))
    await interaction.response.send_message(
        view=SettingsView(interaction.guild, tracked),
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )


@tree.command(name="facthelp", description="What is this bot and why is it here")
async def facthelp_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        view=FactHelpView(bot.user.id if bot.user else None),
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )


@bot.event
async def setup_hook():
    try:
        utils.db_conn = await db.open_db(config.DB_PATH)
        utils.tracked = await db.load_tracked(utils.db_conn)
    except Exception:
        utils.db_conn = None
        utils.tracked = {}
        log.exception("Stats database unavailable; running without persistence")

    try:
        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            tree.copy_global_to(guild=guild)
            synced = await tree.sync(guild=guild)
        else:
            synced = await tree.sync()
        log.info("Synced %d slash command(s).", len(synced))
    except discord.HTTPException:
        log.exception("Command sync failed; the previous commands stay registered")

    log.info(
        "Tracking %d configured guild(s); promo chance %.2f",
        len(utils.tracked),
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
        watched = utils.tracked.get(message.guild.id)
        if watched:
            parent_id = getattr(message.channel, "parent_id", None)
            if message.channel.id not in watched and parent_id not in watched:
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
    }
    if _promo_due():
        # Components-V2 cards cannot carry embeds, so promos go out as text.
        payload["content"] = answer.text
        payload["embed"] = support_embed()
    else:
        payload["view"] = FactReplyView(answer)

    try:
        await message.reply(**payload)
    except discord.HTTPException:
        log.warning("Could not reply in channel %s", message.channel.id, exc_info=True)
        return

    if utils.db_conn is None or message.guild is None:
        return
    guild_id = message.guild.id
    try:
        await db.record(
            utils.db_conn,
            guild_id,
            message.author.id,
            found[0].n,
            found[0].label,
            discord.utils.utcnow(),
        )
    except Exception:
        log.warning("Could not record a factorial", exc_info=True)
