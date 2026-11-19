<div align="center">

<img id="Hero" src="./assets/banner.png" alt="FactorialBot banner" width="880">

# FactorialBot

**A Discord bot that answers every `10!` in chat, whether you asked or not.**

[![Invite FactorialBot](https://img.shields.io/badge/Discord-Invite%20Bot-green?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1572984961030422610&permissions=68608&integration_type=0&scope=applications.commands+bot)
[![Join the server](https://img.shields.io/badge/Discord-Join%20server-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://bittu.dev/discord/)

</div>

## How It Works

- The bot reads every message it can see, in every channel.
- Anything shaped like `10!` or `9!!` gets a reply, in plain text, with attitude.
- Small factorials are printed in full: `10! = 3,628,800`.
- Big ones get the digit count, the trailing zeros and a scientific shrug,
  because nobody needs 158 digits in chat.
- One reply per message, and one reply every few seconds per channel.
- Roughly 1 in 10 replies carries a Patreon embed. The math is free; the hosting is not.

```
you: 100!
bot: Let's talk about 100!: 158 digits
     It ends in 24 zeros and starts around 9.3326 × 10^157. I'm not typing the rest.
     /factorial · /help
```

## Quickstart

You can [invite the public bot](https://discord.com/oauth2/authorize?client_id=1572984961030422610&permissions=68608&integration_type=0&scope=applications.commands+bot), or host it yourself:

```bash
# Installation
git clone https://github.com/Bittu5134/FactorialBot.git && cd FactorialBot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configuration
# Don't forget to add your DISCORD_TOKEN here
cp .env.example .env

# Start the bot
python main.py
```

Then run `/setting` in your server if you want any channel left alone.

> [!IMPORTANT]
> The bot needs the **Message Content** privileged intent. Enable it in the
> [Discord Developer Portal](https://discord.com/developers/applications) under
> **Bot → Privileged Gateway Intents**, otherwise Discord will not let it read
> messages and it will refuse to start.

> [!NOTE]
> The invite link above already asks for the permissions it needs: View
> Channels, Send Messages and Read Message History. Slash commands need the
> `applications.commands` scope, which it also asks for.

### ENV Variables

- `DISCORD_TOKEN` — Discord bot token.
- `GUILD_ID` — Optional development guild ID for instant command syncing.
- `REPLY_COOLDOWN_SECS` — Optional seconds between two replies in one channel (default `3`).
- `LOG_WEBHOOK_URL` — Optional webhook URL for guild join/leave logs.
- `SUPPORT_CHANCE` — Optional fraction of replies with the Patreon embed (default `0.1`, `0` disables it).
- `DB_PATH` — Optional path for the settings database (default `factorialbot.db`). `.env` is always read from the project root, whatever the working directory.

## Commands

- `/factorial` — demand a specific factorial, with attitude.
- `/setting` *(Manage Server)* — blacklist channels the bot should ignore, or ignore
  the whole server. No limit.
- `/help` — what the bot does, plus invite and support buttons.

## Screenshots

<div align="center">

<img src="./assets/screenshot.png" width="640" alt="FactorialBot answering 78! in chat">

</div>

## A Note On Accuracy

Small factorials are computed exactly. Big ones are described with Stirling's
approximation: the leading digits and the trailing zeros are real, the middle
was never built. This is a joke bot with a calculator habit, not a
peer-reviewed mathematics service.

## Support

FactorialBot is free and runs on caffeine. If it made you smile, you can
[become a patron](https://www.patreon.com/c/LazyBittu).

## Built Using

[discord.py](https://github.com/Rapptz/discord.py) · [aiosqlite](https://github.com/omnilib/aiosqlite)
