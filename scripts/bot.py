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
