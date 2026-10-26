"""Find the snapshot block for every moment of the edition.

The block that stands for a moment is the newest block stamped strictly before
it. We bisect on block timestamps from the node, confirm that the block after
it is stamped at or after the moment, and compare with the explorer's own
answer. Moments: quarter start and end, every month end in between, every
seventh day and every day.
"""

from datetime import datetime, timedelta, timezone

from .. import edition, ledger
from ..node import Node
from ..routescan import Routescan

DAY = 86400


def unix(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc)


def wanted_moments(cfg):
    start, end = unix(cfg["period"]["start_utc"]), unix(cfg["period"]["end_utc"])
    out = [("start", "main", start), ("end", "main", end)]
    month = utc(start).replace(day=1)
    while True:
        month = (month + timedelta(days=32)).replace(day=1)
        if month.timestamp() >= end:
            break
        out.append((f"month_{month:%Y-%m-%d}", "month", int(month.timestamp())))
    out += [(f"week_{utc(t):%Y-%m-%d}", "week", t) for t in range(start, end + 1, 7 * DAY)]
    if (end - start) % (7 * DAY):
        out.append(("week_end", "week", end))
    out += [(f"day_{utc(t):%Y-%m-%d}", "day", t) for t in range(start, end + 1, DAY)]
    return out


def run(flags):
    cfg = edition.read()
    node, explorer, con = Node(cfg["chain"]["rpc_url"]), Routescan(cfg), ledger.open_cache()
    tip = int(node.one("eth_blockNumber"), 16)
    stamps = {}

    def stamp(height):
        if height not in stamps:
            stamps[height] = int(node.block(height)["timestamp"], 16)
        return stamps[height]

    def newest_before(moment):
        low, high = 0, tip            # stamp(low) < moment <= stamp(high)
        while high - low > 1:
            middle = (low + high) // 2
            low, high = (middle, high) if stamp(middle) < moment else (low, middle)
        return low

    for label, kind, moment in wanted_moments(cfg):
        height = newest_before(moment)
        if not stamp(height) < moment <= stamp(height + 1):
            raise SystemExit(f"{label}: block {height} does not sit just before the moment")
        theirs = explorer.block_before(moment)
        # The explorer treats a block stamped exactly at the moment as "before" it; we do not.
        if theirs != height and not (theirs == height + 1 and stamp(theirs) == moment):
            raise SystemExit(f"{label}: node gives {height}, explorer gives {theirs}")
        con.execute("INSERT OR REPLACE INTO moments VALUES (?, ?, ?, ?, ?)", (label, kind, height, stamp(height), moment))
        if kind != "day":
            print(f"  {label:20} block {height:>9}  {utc(stamp(height)):%Y-%m-%d %H:%M:%S} UTC")
    con.commit()
    cfg["snapshot_blocks"]["start"] = ledger.block_of(con, "start")
    cfg["snapshot_blocks"]["end"] = ledger.block_of(con, "end")
    edition.write(cfg)
