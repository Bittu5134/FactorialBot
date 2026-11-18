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
