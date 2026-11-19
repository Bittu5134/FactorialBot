import logging

import aiosqlite

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id        INTEGER PRIMARY KEY,
    allowed_channels TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


async def _migrate(db: aiosqlite.Connection) -> None:
    """Bring old tables up to date without losing the stored choices."""
    columns = {
        row["name"]
        for row in await db.execute_fetchall("PRAGMA table_info(guild_settings)")
    }

    if "tracked_channels" in columns:
        await db.execute(
            "ALTER TABLE guild_settings "
            "RENAME COLUMN tracked_channels TO allowed_channels"
        )
        log.info("Migrated guild_settings.tracked_channels")

    if "excluded_channels" in columns:
        # The old column stored channels to ignore; a whitelist means the opposite.
        await db.execute(
            "ALTER TABLE guild_settings "
            "RENAME COLUMN excluded_channels TO allowed_channels"
        )
        await db.execute("UPDATE guild_settings SET allowed_channels = ''")
        log.info("Reset the old channel blacklist; every channel is allowed again")

    if "ignore_all" in columns:
        await db.execute("ALTER TABLE guild_settings DROP COLUMN ignore_all")
        log.info("Dropped guild_settings.ignore_all")

    await db.commit()


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


async def load_allowed(db: aiosqlite.Connection) -> dict[int, set[int]]:
    """Every guild's whitelisted channel ids, for the in-memory cache."""
    rows = await db.execute_fetchall(
        "SELECT guild_id, allowed_channels FROM guild_settings"
    )
    allowed: dict[int, set[int]] = {}
    for row in rows:
        ids = {int(part) for part in row["allowed_channels"].split(",") if part}
        if ids:
            allowed[row["guild_id"]] = ids
    return allowed


async def set_allowed(
    db: aiosqlite.Connection, guild_id: int, channel_ids: list[int]
) -> None:
    """An empty list means every channel in the guild is allowed."""
    packed = ",".join(str(channel_id) for channel_id in channel_ids)
    await db.execute(
        """
        INSERT INTO guild_settings (guild_id, allowed_channels)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            allowed_channels = excluded.allowed_channels
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
