import discord

from . import config, db, utils

COLOUR = discord.Colour.from_str("#3B82F6")


def _excluded_text(guild: discord.Guild, excluded: list[int]) -> str:
    live = sorted(cid for cid in excluded if guild.get_channel(cid))
    gone = len(excluded) - len(live)
    if not live:
        return "**Ignoring nothing.** Every channel gets answered."
    lines = "\n".join(f"- <#{cid}>" for cid in live)
    plural = "s" if len(live) != 1 else ""
    text = f"**Ignoring {len(live)} channel{plural}:**\n{lines}"
    if gone:
        text += f"\n-# {gone} more point at deleted channels"
    return text


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
    """Pick channels the bot should ignore; an empty pick means everywhere."""

    def __init__(self, guild: discord.Guild, excluded: list[int]) -> None:
        super().__init__(timeout=None)

        self.select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="Pick the channels to ignore",
            min_values=0,
            max_values=config.MAX_PICKER_CHOICES,
            default_values=[
                discord.Object(id=cid)
                for cid in excluded[: config.MAX_PICKER_CHOICES]
                if guild.get_channel(cid)
            ],
        )
        self.select.callback = self.on_channels

        clear = discord.ui.Button(
            label="Ignore nothing",
            style=discord.ButtonStyle.secondary,
            emoji="🌐",
        )
        clear.callback = self.on_clear

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("## FactorialBot Settings"),
                discord.ui.TextDisplay(_excluded_text(guild, excluded)),
                discord.ui.ActionRow(self.select),
                discord.ui.ActionRow(clear),
                discord.ui.TextDisplay(
                    "-# Picked channels are ignored everywhere. "
                    "Nothing picked means every channel."
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

        ids = [channel.id for channel in self.select.values]
        await db.set_excluded(utils.db_conn, interaction.guild_id, ids)
        utils.excluded[interaction.guild_id] = set(ids)
        await interaction.response.edit_message(
            view=SettingsView(interaction.guild, ids)
        )

    async def on_clear(self, interaction: discord.Interaction) -> None:
        if await _deny_non_admin(interaction):
            return
        if utils.db_conn is None:
            await interaction.response.send_message(
                "The settings database is not ready yet.", ephemeral=True
            )
            return

        await db.set_excluded(utils.db_conn, interaction.guild_id, [])
        utils.excluded.pop(interaction.guild_id, None)
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
                "**/setting** — blacklist channels the bot should ignore\n"
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
