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

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


def _promo_due() -> bool:
    return random.random() < config.SUPPORT_CHANCE


@tree.command(name="factorial", description="Get one factorial, with attitude")
async def factorial_command(interaction: discord.Interaction, number: int) -> None:
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
    utils.db_conn = await db.open_db(config.DB_PATH)
    utils.tracked = await db.load_tracked(utils.db_conn)

    if config.GUILD_ID:
        guild = discord.Object(id=config.GUILD_ID)
        tree.copy_global_to(guild=guild)
        synced = await tree.sync(guild=guild)
    else:
        synced = await tree.sync()
    log.info("Synced %d slash command(s).", len(synced))


@bot.event
async def on_ready():
    log.info("Logged in as %s in %d guild(s)", bot.user, len(bot.guilds))


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
        f"➖ **Removed** {guild.name} (`{guild.id}`) · "
        f"{len(bot.guilds)} guilds total"
    )
