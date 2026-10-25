"""Local SQLite cache of everything read from the chain and the explorer.

The cache holds per-address data, so it lives in cache/ and is never
published. Every step writes here and can be stopped and restarted.
"""

import sqlite3

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS progress (name TEXT PRIMARY KEY, value INTEGER);
-- src is a bit mask of how the address was found, see SRC below.
CREATE TABLE IF NOT EXISTS addresses (addr TEXT PRIMARY KEY, src INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS snapshots (name TEXT PRIMARY KEY, kind TEXT, block INTEGER, ts INTEGER, boundary INTEGER);
-- Transactions inside the quarter, with value and fee.
CREATE TABLE IF NOT EXISTS qtx (hash TEXT PRIMARY KEY, block INTEGER, idx INTEGER, sender TEXT, recipient TEXT,
    value TEXT, fee TEXT, status INTEGER, created TEXT, input4 TEXT);
CREATE TABLE IF NOT EXISTS qblock (block INTEGER PRIMARY KEY, ts INTEGER, fees TEXT);
-- Every log ever emitted by WRBNT or the two pools.
CREATE TABLE IF NOT EXISTS logs (block INTEGER, tx TEXT, idx INTEGER, address TEXT, topics TEXT, data TEXT,
    PRIMARY KEY (tx, idx));
-- Internal transfers with value, quarter only, from the explorer.
CREATE TABLE IF NOT EXISTS internal (block INTEGER, hash TEXT, sender TEXT, recipient TEXT, value TEXT,
    type TEXT, is_error INTEGER, trace TEXT, PRIMARY KEY (hash, trace, sender, recipient, value));
-- Addresses named in block headers (the governor set), with the blocks they appear in.
CREATE TABLE IF NOT EXISTS header_addr (addr TEXT PRIMARY KEY, first_block INTEGER, last_block INTEGER, blocks INTEGER);
CREATE TABLE IF NOT EXISTS balance (addr TEXT, block INTEGER, wei TEXT, PRIMARY KEY (addr, block));
-- kind: wrbnt, stake:<pool address>
CREATE TABLE IF NOT EXISTS token (addr TEXT, block INTEGER, kind TEXT, wei TEXT, PRIMARY KEY (addr, block, kind));
CREATE TABLE IF NOT EXISTS unlocks (pool TEXT, addr TEXT, amount TEXT, unlock_ts INTEGER);
CREATE TABLE IF NOT EXISTS code (addr TEXT PRIMARY KEY, kind TEXT);
CREATE TABLE IF NOT EXISTS contract (addr TEXT PRIMARY KEY, name TEXT, verified INTEGER);
CREATE TABLE IF NOT EXISTS label (addr TEXT PRIMARY KEY, name TEXT, list_balance TEXT);
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT);
"""

SRC = {
    "tx_from": 1, "tx_to": 2, "created": 4, "internal": 8, "header": 16,
    "wrbnt_log": 32, "pool_log": 64, "explorer_list": 128, "named": 256, "genesis": 512,
}


def connect():
    d = config.ROOT / "cache"
    d.mkdir(exist_ok=True)
    db = sqlite3.connect(d / f"{config.DEFAULT_EDITION}.sqlite", timeout=600)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.executescript(SCHEMA)
    return db


def get_progress(db, name, default=-1):
    row = db.execute("SELECT value FROM progress WHERE name=?", (name,)).fetchone()
    return row[0] if row else default


def set_progress(db, name, value):
    db.execute("INSERT OR REPLACE INTO progress VALUES (?, ?)", (name, value))


def add_addresses(db, pairs):
    """pairs: iterable of (address, src bit). Merges bits into existing rows."""
    merged = {}
    for a, bit in pairs:
        if not a:
            continue
        a = a.lower()
        merged[a] = merged.get(a, 0) | bit
    db.executemany(
        "INSERT INTO addresses VALUES (?, ?) ON CONFLICT(addr) DO UPDATE SET src = src | excluded.src",
        merged.items())


def kv_set(db, key, value):
    db.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (key, str(value)))


def kv_get(db, key, default=None):
    row = db.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def snapshot(db, name):
    return db.execute("SELECT block FROM snapshots WHERE name=?", (name,)).fetchone()[0]


def snapshots(db, kind=None):
    q = "SELECT name, block, ts FROM snapshots"
    rows = db.execute(q + (" WHERE kind=?" if kind else "") + " ORDER BY block", (kind,) if kind else ()).fetchall()
    return rows
