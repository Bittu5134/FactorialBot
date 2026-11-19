import time

from . import config

db_conn = None

# guild_id -> ignored channel ids; an empty set means every channel.
excluded: dict[int, set[int]] = {}

# guild ids where the bot keeps quiet everywhere.
muted: set[int] = set()

_last_reply: dict[int, float] = {}


def reply_allowed(channel_id: int, now: float | None = None) -> bool:
    """True when this channel has been quiet long enough for a new reply."""
    now = time.monotonic() if now is None else now
    last = _last_reply.get(channel_id)
    if last is not None and now - last < config.REPLY_COOLDOWN_SECS:
        return False
    _last_reply[channel_id] = now
    _prune(now)
    return True


def _prune(now: float) -> None:
    if len(_last_reply) < 1024:
        return
    cutoff = now - max(config.REPLY_COOLDOWN_SECS * 4, 60)
    for channel_id, stamp in list(_last_reply.items()):
        if stamp < cutoff:
            del _last_reply[channel_id]


def reset_rate_limits() -> None:
    _last_reply.clear()


def invite_url(client_id: int) -> str:
    return (
        f"https://discord.com/oauth2/authorize?client_id={client_id}"
        f"&permissions={config.INVITE_PERMISSIONS}"
        "&integration_type=0&scope=bot+applications.commands"
    )


__all__ = [
    "db_conn",
    "excluded",
    "invite_url",
    "muted",
    "reply_allowed",
    "reset_rate_limits",
]
