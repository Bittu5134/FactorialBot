import logging

import aiosqlite

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id          INTEGER PRIMARY KEY,
    excluded_channels TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


async def _migrate(db: aiosqlite.Connection) -> None:
    """Rename the old whitelist column; the data means the same thing."""
    rows = await db.execute_fetchall("PRAGMA table_info(guild_settings)")
    for row in rows:
        if row["name"] == "tracked_channels":
            await db.execute(
                "ALTER TABLE guild_settings "
                "RENAME COLUMN tracked_channels TO excluded_channels"
            )
            await db.commit()
            log.info("Migrated guild_settings.tracked_channels")
            return


async def open_db(path) -> aiosqlite.Connection:
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.executescript(SCHEMA)
    await db.commit()
    await _migrate(db)
    log.info("Opened settings database at %s", path)
    return db


async def close_db(db: aiosqlite.Connection | None) -> None:
    if db is not None:
        await db.close()


async def load_excluded(db: aiosqlite.Connection) -> dict[int, set[int]]:
    """Every guild's ignored channel ids, for the in-memory cache."""
    rows = await db.execute_fetchall(
        "SELECT guild_id, excluded_channels FROM guild_settings"
    )
    excluded: dict[int, set[int]] = {}
    for row in rows:
        ids = {int(part) for part in row["excluded_channels"].split(",") if part}
        if ids:
            excluded[row["guild_id"]] = ids
    return excluded


async def get_excluded(db: aiosqlite.Connection, guild_id: int) -> set[int]:
    rows = await db.execute_fetchall(
        "SELECT excluded_channels FROM guild_settings WHERE guild_id = ?", (guild_id,)
    )
    if not rows:
        return set()
    return {int(part) for part in rows[0]["excluded_channels"].split(",") if part}


async def set_excluded(
    db: aiosqlite.Connection, guild_id: int, channel_ids: list[int]
) -> None:
    """An empty list means every channel is answered in."""
    packed = ",".join(str(channel_id) for channel_id in channel_ids)
    await db.execute(
        """
        INSERT INTO guild_settings (guild_id, excluded_channels)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            excluded_channels = excluded.excluded_channels
        """,
        (guild_id, packed),
    )
    await db.commit()


async def get_meta(db: aiosqlite.Connection, key: str) -> str | None:
    rows = await db.execute_fetchall("SELECT value FROM meta WHERE key = ?", (key,))
    return rows[0]["value"] if rows else None


async def set_meta(db: aiosqlite.Connection, key: str, value: str) -> None:
    await db.execute(
        """
        INSERT INTO meta (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    await db.commit()


__all__ = [
    "close_db",
    "get_excluded",
    "get_meta",
    "load_excluded",
    "open_db",
    "set_excluded",
    "set_meta",
]
