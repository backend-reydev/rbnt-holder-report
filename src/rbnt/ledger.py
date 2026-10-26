"""The local cache: one SQLite file per edition under cache/.

It holds per-address data, so it is never published. Every stage reads and
writes here and remembers how far it got, so any stage can be stopped and run
again.
"""

import sqlite3

from . import edition

TABLES = """
CREATE TABLE IF NOT EXISTS cursor (stage TEXT PRIMARY KEY, at INTEGER);
CREATE TABLE IF NOT EXISTS facts (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS moments (label TEXT PRIMARY KEY, kind TEXT, block INTEGER, ts INTEGER, cutoff INTEGER);
-- Every address that could hold RBNT. `how` is a bit mask of where it was seen (FOUND_BY).
CREATE TABLE IF NOT EXISTS seen (addr TEXT PRIMARY KEY, how INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS header_seen (addr TEXT PRIMARY KEY, first_block INTEGER, last_block INTEGER, blocks INTEGER);
CREATE TABLE IF NOT EXISTS watched_logs (block INTEGER, tx TEXT, idx INTEGER, address TEXT, topics TEXT, data TEXT,
    PRIMARY KEY (tx, idx));
CREATE TABLE IF NOT EXISTS quarter_tx (hash TEXT PRIMARY KEY, block INTEGER, idx INTEGER, sender TEXT, recipient TEXT,
    value TEXT, fee TEXT, status INTEGER, created TEXT, input4 TEXT);
CREATE TABLE IF NOT EXISTS quarter_block (block INTEGER PRIMARY KEY, ts INTEGER, fees TEXT);
CREATE TABLE IF NOT EXISTS inner_transfers (block INTEGER, hash TEXT, sender TEXT, recipient TEXT, value TEXT,
    type TEXT, is_error INTEGER, trace TEXT, PRIMARY KEY (hash, trace, sender, recipient, value));
CREATE TABLE IF NOT EXISTS native_at (addr TEXT, block INTEGER, wei TEXT, PRIMARY KEY (addr, block));
CREATE TABLE IF NOT EXISTS token_at (addr TEXT, block INTEGER, kind TEXT, wei TEXT, PRIMARY KEY (addr, block, kind));
CREATE TABLE IF NOT EXISTS locks (pool TEXT, addr TEXT, amount TEXT, unlock_ts INTEGER);
CREATE TABLE IF NOT EXISTS bytecode_kind (addr TEXT PRIMARY KEY, kind TEXT);
CREATE TABLE IF NOT EXISTS program_name (addr TEXT PRIMARY KEY, name TEXT, verified INTEGER);
CREATE TABLE IF NOT EXISTS tags (addr TEXT PRIMARY KEY, name TEXT, list_balance TEXT);
"""

FOUND_BY = {"sender": 1, "recipient": 2, "deployed": 4, "inner": 8, "header": 16,
            "wrbnt_event": 32, "pool_event": 64, "explorer": 128, "named": 256}


def open_cache():
    folder = edition.HOME / "cache"
    folder.mkdir(exist_ok=True)
    con = sqlite3.connect(folder / f"{edition.EDITION}.sqlite", timeout=600)
    con.execute("PRAGMA journal_mode = WAL")
    con.executescript(TABLES)
    return con


def position(con, stage, default=-1):
    hit = con.execute("SELECT at FROM cursor WHERE stage = ?", (stage,)).fetchone()
    return default if hit is None else hit[0]


def advance(con, stage, at):
    con.execute("INSERT INTO cursor (stage, at) VALUES (?, ?) ON CONFLICT(stage) DO UPDATE SET at = excluded.at",
                (stage, at))


def remember(con, k, v):
    con.execute("INSERT INTO facts (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v", (k, str(v)))


def recall(con, k, default=None):
    hit = con.execute("SELECT v FROM facts WHERE k = ?", (k,)).fetchone()
    return default if hit is None else hit[0]


def note_addresses(con, pairs):
    """pairs: (address, FOUND_BY bit). Bits are OR-ed into what is already known."""
    bits = {}
    for addr, bit in pairs:
        if addr:
            bits[addr.lower()] = bits.get(addr.lower(), 0) | bit
    con.executemany("INSERT INTO seen (addr, how) VALUES (?, ?) "
                    "ON CONFLICT(addr) DO UPDATE SET how = how | excluded.how", bits.items())


def block_of(con, label):
    return con.execute("SELECT block FROM moments WHERE label = ?", (label,)).fetchone()[0]


def moments(con, kind):
    return con.execute("SELECT label, block, ts FROM moments WHERE kind = ? ORDER BY block", (kind,)).fetchall()
