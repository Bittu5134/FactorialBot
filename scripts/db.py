import logging
from dataclasses import dataclass
from datetime import datetime

import aiosqlite

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_stats (
    guild_id      INTEGER PRIMARY KEY,
    total         INTEGER NOT NULL DEFAULT 0,
    biggest_n     INTEGER NOT NULL DEFAULT 0,
    biggest_label TEXT    NOT NULL DEFAULT '',
    last_label    TEXT    NOT NULL DEFAULT '',
    last_ts       TEXT
);

CREATE TABLE IF NOT EXISTS user_stats (
    guild_id  INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    count     INTEGER NOT NULL DEFAULT 0,
    biggest_n INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id         INTEGER PRIMARY KEY,
    tracked_channels TEXT NOT NULL DEFAULT ''
);
"""


@dataclass
class GuildStats:
    total: int = 0
    biggest_n: int = 0
    biggest_label: str = ""
    last_label: str = ""

    @property
    def biggest(self) -> str:
        return self.biggest_label or "nothing yet"

    @property
    def last(self) -> str:
        return self.last_label or "nothing yet"


async def open_db(path) -> aiosqlite.Connection:
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.executescript(SCHEMA)
    await db.commit()
    log.info("Opened stats database at %s", path)
    return db


async def close_db(db: aiosqlite.Connection | None) -> None:
    if db is not None:
        await db.close()


async def record(
    db: aiosqlite.Connection,
    guild_id: int,
    user_id: int,
    n: int,
    label: str,
    ts: datetime | None = None,
) -> None:
    """Count one spotted factorial for the guild and for its author."""
    await db.execute(
        """
        INSERT INTO guild_stats
            (guild_id, total, biggest_n, biggest_label, last_label, last_ts)
        VALUES (?, 1, ?, ?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
            total         = total + 1,
            biggest_n     = MAX(guild_stats.biggest_n, excluded.biggest_n),
            biggest_label = CASE
                WHEN excluded.biggest_n > guild_stats.biggest_n
                THEN excluded.biggest_label
                ELSE guild_stats.biggest_label
            END,
            last_label    = excluded.last_label,
            last_ts       = excluded.last_ts
        """,
        (guild_id, n, label, label, ts.isoformat() if ts else None),
    )
    await db.execute(
        """
        INSERT INTO user_stats (guild_id, user_id, count, biggest_n)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(guild_id, user_id) DO UPDATE SET
            count     = count + 1,
            biggest_n = MAX(user_stats.biggest_n, excluded.biggest_n)
        """,
        (guild_id, user_id, n),
    )
    await db.commit()


async def get_guild_stats(db: aiosqlite.Connection, guild_id: int) -> GuildStats:
    rows = await db.execute_fetchall(
        "SELECT * FROM guild_stats WHERE guild_id = ?", (guild_id,)
    )
    if not rows:
        return GuildStats()
    row = rows[0]
    return GuildStats(
        total=row["total"],
        biggest_n=row["biggest_n"],
        biggest_label=row["biggest_label"],
        last_label=row["last_label"],
    )


async def top(
    db: aiosqlite.Connection, guild_id: int, limit: int = 5
) -> list[tuple[int, int]]:
    rows = await db.execute_fetchall(
        """
        SELECT user_id, count FROM user_stats
        WHERE guild_id = ?
        ORDER BY count DESC, user_id ASC
        LIMIT ?
        """,
        (guild_id, limit),
    )
    return [(row["user_id"], row["count"]) for row in rows]


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


async def reset_guild(db: aiosqlite.Connection, guild_id: int) -> None:
    await db.execute("DELETE FROM guild_stats WHERE guild_id = ?", (guild_id,))
    await db.execute("DELETE FROM user_stats WHERE guild_id = ?", (guild_id,))
    await db.commit()


__all__ = [
    "GuildStats",
    "close_db",
    "get_guild_stats",
    "get_tracked",
    "load_tracked",
    "open_db",
    "record",
    "reset_guild",
    "set_tracked",
    "top",
]
