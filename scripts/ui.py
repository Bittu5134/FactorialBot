import discord

from . import config, db, utils

COLOUR = discord.Colour.from_str("#3B82F6")


def _tracked_text(guild: discord.Guild, tracked: list[int]) -> str:
    live = sorted(channel_id for channel_id in tracked if guild.get_channel(channel_id))
    if not live:
        return "**Every channel.** Pick any below to narrow it down."
    lines = "\n".join(f"- <#{channel_id}>" for channel_id in live)
    return f"**Watching {len(live)} channel{'s' if len(live) != 1 else ''}:**\n{lines}"


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


async def _deny_non_admin(interaction: discord.Interaction) -> bool:
    """Returns True and replies if the user lacks Manage Server."""
    perms = getattr(interaction.user, "guild_permissions", None)
    if perms and perms.manage_guild:
        return False
    await interaction.response.send_message(
        "You need **Manage Server** to change this.", ephemeral=True
    )
    return True


class SettingsView(discord.ui.LayoutView):
    """Pick up to five channels to track; an empty pick means everything."""

    def __init__(self, guild: discord.Guild, tracked: list[int]) -> None:
        super().__init__(timeout=None)

        self.select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder=f"Pick up to {config.MAX_TRACKED_CHANNELS} channels",
            min_values=0,
            max_values=config.MAX_TRACKED_CHANNELS,
            default_values=[
                discord.Object(id=channel_id)
                for channel_id in tracked[: config.MAX_TRACKED_CHANNELS]
                if guild.get_channel(channel_id)
            ],
        )
        self.select.callback = self.on_channels

        track_all = discord.ui.Button(
            label="Track everything",
            style=discord.ButtonStyle.secondary,
            emoji="🌐",
        )
        track_all.callback = self.on_track_all

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("## FactorialBot Settings"),
                discord.ui.TextDisplay(_tracked_text(guild, tracked)),
                discord.ui.ActionRow(self.select),
                discord.ui.ActionRow(track_all),
                discord.ui.TextDisplay(
                    "-# Maximum "
                    f"{config.MAX_TRACKED_CHANNELS} channels. "
                    "Leaving the picker empty tracks every channel."
                ),
                accent_colour=COLOUR,
            )
        )

    async def on_channels(self, interaction: discord.Interaction) -> None:
        if await _deny_non_admin(interaction):
            return
        if utils.db_conn is None:
            await interaction.response.send_message(
                "The settings database is not ready yet.", ephemeral=True
            )
            return

        ids = [channel.id for channel in self.select.values][
            : config.MAX_TRACKED_CHANNELS
        ]
        await db.set_tracked(utils.db_conn, interaction.guild_id, ids)
        utils.tracked[interaction.guild_id] = set(ids)
        await interaction.response.edit_message(
            view=SettingsView(interaction.guild, ids)
        )

    async def on_track_all(self, interaction: discord.Interaction) -> None:
        if await _deny_non_admin(interaction):
            return
        if utils.db_conn is None:
            await interaction.response.send_message(
                "The settings database is not ready yet.", ephemeral=True
            )
            return

        await db.set_tracked(utils.db_conn, interaction.guild_id, [])
        utils.tracked.pop(interaction.guild_id, None)
        await interaction.response.edit_message(
            view=SettingsView(interaction.guild, [])
        )


class HelpView(discord.ui.LayoutView):
    def __init__(self, client_id: int | None = None) -> None:
        super().__init__(timeout=None)

        items: list[discord.ui.Item] = [
            discord.ui.TextDisplay("### FactorialBot"),
            discord.ui.TextDisplay(
                "I read every message and pounce on anything shaped like "
                "`10!` or `9!!`.\n"
                "Small factorials get typed out in full. Big ones get "
                "**digits**, **trailing zeros** and a scientific shrug, "
                "because nobody needs 158 digits in chat."
            ),
            discord.ui.Separator(),
            discord.ui.TextDisplay(
                "**/factorial** — demand a specific factorial\n"
                "**/setting** — pick up to five channels to watch\n"
                "**Rate limit** — one reply every "
                f"{config.REPLY_COOLDOWN_SECS:g}s per channel"
            ),
            discord.ui.TextDisplay("-# Accuracy not guaranteed. Annoyance guaranteed."),
        ]

        links: list[discord.ui.Button] = []
        if client_id:
            links.append(
                discord.ui.Button(
                    label="Invite me",
                    url=utils.invite_url(client_id),
                    style=discord.ButtonStyle.link,
                )
            )
        links.append(
            discord.ui.Button(
                label="Support",
                url=config.PATREON_URL,
                emoji="💖",
                style=discord.ButtonStyle.link,
            )
        )
        items.append(discord.ui.ActionRow(*links))

        self.add_item(discord.ui.Container(*items, accent_colour=COLOUR))


__all__ = ["COLOUR", "HelpView", "SettingsView", "support_embed"]
