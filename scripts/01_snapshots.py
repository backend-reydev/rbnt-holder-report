"""Step 1. Find every snapshot block for the edition.

A snapshot at time T is the highest block whose timestamp is earlier than T.
Found by binary search on block timestamps from the node, then cross-checked
against the explorer's getblocknobytime for each time.

Snapshots: quarter start and end, each month end in between, and every seven
days and every day from the start (used for staking pools and named wallets).
"""

from datetime import datetime, timedelta, timezone

import _path  # noqa: F401
from rbnt import config, store
from rbnt.explorer import Explorer
from rbnt.rpc import Rpc


def iso_ts(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def main():
    cfg = config.load()
    rpc, ex, db = Rpc(cfg["chain"]["rpc_url"]), Explorer(cfg), store.connect()
    head = int(rpc.call("eth_blockNumber", []), 16)
    ts_cache = {}

    def ts(n):
        if n not in ts_cache:
            ts_cache[n] = int(rpc.block(n)["timestamp"], 16)
        return ts_cache[n]

    def block_before(t):
        lo, hi = 0, head  # invariant: ts(lo) < t <= ts(hi)
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if ts(mid) < t:
                lo = mid
            else:
                hi = mid
        return lo

    start, end = iso_ts(cfg["period"]["start_utc"]), iso_ts(cfg["period"]["end_utc"])
    wanted = [("start", "main", start), ("end", "main", end)]
    d = datetime.fromtimestamp(start, timezone.utc)
    while True:
        d = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
        if d.timestamp() >= end:
            break
        wanted.append((f"month_{d:%Y-%m-%d}", "month", int(d.timestamp())))
    t = start
    while t <= end:
        wanted.append((f"week_{datetime.fromtimestamp(t, timezone.utc):%Y-%m-%d}", "week", t))
        t += 7 * 86400
    if wanted[-1][2] != end:
        wanted.append(("week_end", "week", end))
    for t in range(start, end + 1, 86400):
        wanted.append((f"day_{datetime.fromtimestamp(t, timezone.utc):%Y-%m-%d}", "day", t))

    for name, kind, boundary in wanted:
        b = block_before(boundary)
        assert ts(b) < boundary <= ts(b + 1), name
        check = ex.block_before(boundary)
        # The explorer counts a block stamped exactly at T as "before" T. This
        # report does not, so that case is the only difference allowed.
        if check != b and not (check == b + 1 and ts(check) == boundary):
            raise SystemExit(f"{name}: node says {b}, explorer says {check}")
        db.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?)", (name, kind, b, ts(b), boundary))
        print(f"{name:22} block {b:>9}  {datetime.fromtimestamp(ts(b), timezone.utc):%Y-%m-%d %H:%M:%S} UTC"
              f"  next block {datetime.fromtimestamp(ts(b + 1), timezone.utc):%H:%M:%S}")
    db.commit()
    cfg["snapshot_blocks"]["start"] = store.snapshot(db, "start")
    cfg["snapshot_blocks"]["end"] = store.snapshot(db, "end")
    config.save(cfg)


if __name__ == "__main__":
    main()
