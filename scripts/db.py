import logging

import aiosqlite

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id         INTEGER PRIMARY KEY,
    tracked_channels TEXT NOT NULL DEFAULT ''
);
"""


async def open_db(path) -> aiosqlite.Connection:
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.executescript(SCHEMA)
    await db.commit()
    log.info("Opened settings database at %s", path)
    return db


async def close_db(db: aiosqlite.Connection | None) -> None:
    if db is not None:
        await db.close()


async def load_tracked(db: aiosqlite.Connection) -> dict[int, set[int]]:
    """Every guild's tracked channel ids, for the in-memory cache."""
    rows = await db.execute_fetchall(
        "SELECT guild_id, tracked_channels FROM guild_settings"
    )
    tracked: dict[int, set[int]] = {}
    for row in rows:
        ids = {int(part) for part in row["tracked_channels"].split(",") if part}
        if ids:
            tracked[row["guild_id"]] = ids
    return tracked


async def get_tracked(db: aiosqlite.Connection, guild_id: int) -> set[int]:
    rows = await db.execute_fetchall(
        "SELECT tracked_channels FROM guild_settings WHERE guild_id = ?", (guild_id,)
    )
    if not rows:
        return set()
    return {int(part) for part in rows[0]["tracked_channels"].split(",") if part}


async def set_tracked(
    db: aiosqlite.Connection, guild_id: int, channel_ids: list[int]
) -> None:
    """An empty list means every channel in the guild."""
    packed = ",".join(str(channel_id) for channel_id in channel_ids)
    await db.execute(
        """
        INSERT INTO guild_settings (guild_id, tracked_channels)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            tracked_channels = excluded.tracked_channels
        """,
        (guild_id, packed),
    )
    await db.commit()


__all__ = [
    "close_db",
    "get_tracked",
    "load_tracked",
    "open_db",
    "set_tracked",
]
