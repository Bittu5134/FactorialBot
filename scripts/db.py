import logging

import aiosqlite

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id          INTEGER PRIMARY KEY,
    excluded_channels TEXT NOT NULL DEFAULT '',
    ignore_all        INTEGER NOT NULL DEFAULT 0
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
            "RENAME COLUMN tracked_channels TO excluded_channels"
        )
        columns.discard("tracked_channels")
        columns.add("excluded_channels")
        log.info("Migrated guild_settings.tracked_channels")

    if "ignore_all" not in columns:
        await db.execute(
            "ALTER TABLE guild_settings "
            "ADD COLUMN ignore_all INTEGER NOT NULL DEFAULT 0"
        )
        log.info("Added guild_settings.ignore_all")

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


async def load_settings(
    db: aiosqlite.Connection,
) -> tuple[dict[int, set[int]], set[int]]:
    """Every guild's ignored channels and the guilds ignoring everything."""
    rows = await db.execute_fetchall(
        "SELECT guild_id, excluded_channels, ignore_all FROM guild_settings"
    )
    excluded: dict[int, set[int]] = {}
    muted: set[int] = set()
    for row in rows:
        ids = {int(part) for part in row["excluded_channels"].split(",") if part}
        if ids:
            excluded[row["guild_id"]] = ids
        if row["ignore_all"]:
            muted.add(row["guild_id"])
    return excluded, muted


async def set_settings(
    db: aiosqlite.Connection,
    guild_id: int,
    channel_ids: list[int],
    ignore_all: bool = False,
) -> None:
    """An empty list with ignore_all off means every channel is answered in."""
    packed = ",".join(str(channel_id) for channel_id in channel_ids)
    await db.execute(
        """
        INSERT INTO guild_settings (guild_id, excluded_channels, ignore_all)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            excluded_channels = excluded.excluded_channels,
            ignore_all        = excluded.ignore_all
        """,
        (guild_id, packed, int(ignore_all)),
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
