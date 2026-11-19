<div align="center">

# FactorialBot

**A Discord bot that answers every `10!` in chat, whether you asked or not.**

[![Invite FactorialBot](https://img.shields.io/badge/Discord-Invite%20Bot-green?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=938747383104307233&permissions=68608&integration_type=0&scope=bot+applications.commands)

</div>

## How It Works

- Watches every channel it can see, except the ones blacklisted with `/setting`.
- Replies to anything shaped like `10!` or `9!!`, in plain text.
- Small factorials are printed in full: **`10! = 3,628,800`**.
- Big ones get digit count, trailing zeros and scientific notation instead.
- One reply per message, with a short per-channel cooldown.
- Roughly 1 in 10 replies carries a Patreon embed.

```
you: 100!
bot: 100! has 158 digits
     That's 24 trailing zeros, starting with 9.3326 × 10^157.
     You're on your own for the middle.
```

## Quickstart

```bash
git clone https://github.com/Bittu5134/FactorialBot.git && cd FactorialBot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# put your DISCORD_TOKEN in .env
python main.py
```

> [!IMPORTANT]
> Enable the **Message Content** privileged intent in the
> [Discord Developer Portal](https://discord.com/developers/applications)
> under **Bot → Privileged Gateway Intents**, or the bot will refuse to start.

### ENV Variables

- `DISCORD_TOKEN` — Discord bot token.
- `GUILD_ID` — optional guild for instant command syncing.
- `REPLY_COOLDOWN_SECS` — seconds between replies in one channel (default `3`).
- `LOG_WEBHOOK_URL` — optional webhook for guild join/leave logs.
- `SUPPORT_CHANCE` — fraction of replies with the Patreon embed (default `0.1`).
- `DB_PATH` — where to keep the settings database (default `factorialbot.db`).
  `.env` is always read from the project root, whatever the working directory.

## Commands

- `/factorial` — demand a specific factorial.
- `/setting` *(Manage Server)* — blacklist channels to ignore, no limit; empty means none.
- `/help` — what the bot does, plus an invite button.

## Accuracy

Small factorials are exact. Big ones are estimated with Stirling's
approximation. This is a joke bot with a calculator habit.

## Support

Free and running on caffeine: [become a patron](https://www.patreon.com/c/LazyBittu).

## Built Using

[discord.py](https://github.com/Rapptz/discord.py) · [aiosqlite](https://github.com/omnilib/aiosqlite)
