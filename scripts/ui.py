import discord

from . import config, db, utils
from .db import GuildStats
from .replies import Answer

COLOUR = discord.Colour.from_str("#3B82F6")


def _rank_prefix(index: int) -> str:
    """Medals on the podium, plain rank numbers below it."""
    return ("🥇", "🥈", "🥉")[index] if index < 3 else f"**#{index + 1}**"


def _tracked_text(guild: discord.Guild, tracked: list[int]) -> str:
    live = sorted(channel_id for channel_id in tracked if guild.get_channel(channel_id))
    if not live:
        return "**Every channel.** Pick any below to narrow it down."
    lines = "\n".join(f"- <#{channel_id}>" for channel_id in live)
    return f"**Watching {len(live)} channel{'s' if len(live) != 1 else ''}:**\n{lines}"


def _entries_text(rows: list[tuple[int, int]]) -> str:
    if not rows:
        return "Nobody has triggered me yet. Give it time."
    return "\n".join(
        f"{_rank_prefix(index)} <@{user_id}> — {count} factorial"
        f"{'s' if count != 1 else ''}"
        for index, (user_id, count) in enumerate(rows)
    )


def support_embed() -> discord.Embed:
    """The occasional, shameless Patreon plug."""
    embed = discord.Embed(
        title="Support FactorialBot",
        url=config.PATREON_URL,
        colour=COLOUR,
        description=(
            "If being corrected by a calculator made your day better, "
            "consider funding the caffeine behind it.\n\n"
            f"**[Become a patron]({config.PATREON_URL})**"
        ),
    )
    embed.set_footer(text="FactorialBot • the math is free, the jokes are not")
    return embed


class FactReplyView(discord.ui.LayoutView):
    """The card the bot drops under every detected factorial."""

    def __init__(self, answer: Answer) -> None:
        super().__init__(timeout=None)

        items: list[discord.ui.Item] = [
            discord.ui.TextDisplay(f"### {answer.headline}"),
        ]
        if answer.detail:
            items.append(discord.ui.TextDisplay(answer.detail))
        if answer.footer:
            items.append(discord.ui.TextDisplay(f"-# {answer.footer}"))

        self.add_item(discord.ui.Container(*items, accent_colour=COLOUR))
