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
    await db.executescript(SCHEMA)
    await db.commit()
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
