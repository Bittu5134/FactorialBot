import discord

from . import config, db, utils

COLOUR = discord.Colour.from_str("#3B82F6")


def _allowed_text(guild: discord.Guild, allowed: list[int]) -> str:
    live = sorted(cid for cid in allowed if guild.get_channel(cid))
    gone = len(allowed) - len(live)
    if not live:
        return "**Every channel.**"
    lines = "\n".join(f"- <#{cid}>" for cid in live)
    plural = "s" if len(live) != 1 else ""
    text = f"**Watching {len(live)} channel{plural}:**\n{lines}"
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


async def _ready(interaction: discord.Interaction) -> bool:
    """False when the clicker is not an admin or the database is missing."""
    perms = getattr(interaction.user, "guild_permissions", None)
    if not (perms and perms.manage_guild):
        await interaction.response.send_message(
            "You need **Manage Server** to change this.", ephemeral=True
        )
        return False
    if utils.db_conn is None:
        await interaction.response.send_message(
            "The settings database is not ready yet.", ephemeral=True
        )
        return False
    return True


class SettingsView(discord.ui.LayoutView):
    """Pick the channels the bot may answer in; an empty pick means all of them."""

    def __init__(self, guild: discord.Guild, allowed: list[int]) -> None:
        super().__init__(timeout=None)

        self.select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="Pick the channels I may answer in",
            min_values=0,
            max_values=config.MAX_PICKER_CHOICES,
            default_values=[
                discord.Object(id=cid)
                for cid in allowed[: config.MAX_PICKER_CHOICES]
                if guild.get_channel(cid)
            ],
        )
        self.select.callback = self.on_channels

        select_all = discord.ui.Button(
            label="Select all",
            style=discord.ButtonStyle.secondary,
            emoji="✅",
        )
        select_all.callback = self.on_select_all

        clear = discord.ui.Button(
            label="Clear selection",
            style=discord.ButtonStyle.secondary,
            emoji="🧹",
        )
        clear.callback = self.on_clear

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay("## FactorialBot Settings"),
                discord.ui.TextDisplay(
                    f"**Channels**\n{_allowed_text(guild, allowed)}"
                ),
                discord.ui.ActionRow(self.select),
                discord.ui.ActionRow(select_all, clear),
                discord.ui.TextDisplay(
                    "-# 🛈 Nothing picked means every channel. "
                    f"The picker holds {config.MAX_PICKER_CHOICES} at a time.\n"
                    "-# Select all ticks every channel. Clear selection ticks none."
                ),
                accent_colour=COLOUR,
            )
        )

    async def _save(self, interaction: discord.Interaction, ids: list[int]) -> None:
        """Persist a whitelist and re-render the card with it."""
        await db.set_allowed(utils.db_conn, interaction.guild_id, ids)
        if ids:
            utils.allowed[interaction.guild_id] = set(ids)
        else:
            utils.allowed.pop(interaction.guild_id, None)
        await interaction.response.edit_message(
            view=SettingsView(interaction.guild, ids)
        )

    async def on_channels(self, interaction: discord.Interaction) -> None:
        if not await _ready(interaction):
            return
        await self._save(interaction, [channel.id for channel in self.select.values])

    async def on_select_all(self, interaction: discord.Interaction) -> None:
        if not await _ready(interaction):
            return
        ids = sorted(
            (channel.id for channel in interaction.guild.text_channels),
        )
        if len(ids) > config.MAX_PICKER_CHOICES:
            # Too many to show at once; an empty whitelist already means everything.
            ids = []
        await self._save(interaction, ids)

    async def on_clear(self, interaction: discord.Interaction) -> None:
        if not await _ready(interaction):
            return
        await self._save(interaction, [])


class HelpView(discord.ui.LayoutView):
    def __init__(self, client_id: int | None = None) -> None:
        super().__init__(timeout=None)

        items: list[discord.ui.Item] = [
            discord.ui.TextDisplay("### FactorialBot"),
            discord.ui.TextDisplay(
                "I read every message and pounce on anything shaped like "
                "`10!` or `9!!`.\n"
                "Small ones get typed out in full. Big ones get **digits**, "
                "**trailing zeros**\nand a scientific shrug. Nobody needs "
                "158 digits in chat."
            ),
            discord.ui.Separator(),
            discord.ui.TextDisplay(
                "**Commands**\n"
                "**/factorial** — demand a specific factorial\n"
                "**/setting** — pick the channels I may answer in\n"
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
        items.append(discord.ui.TextDisplay("-# /factorial • /setting"))

        self.add_item(discord.ui.Container(*items, accent_colour=COLOUR))
