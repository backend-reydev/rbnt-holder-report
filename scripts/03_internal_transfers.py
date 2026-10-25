"""Step 3. Internal transfers from the explorer, genesis to the end snapshot.

Contracts move RBNT through internal calls, which have no transaction of their
own, and the public node has no trace API. The explorer's txlistinternal
endpoint is read by block range. A range that returns the 10,000 row limit is
split in half until every range is complete.

Every party to a successful internal transfer with value, and every contract
created internally, joins the address list. Inside the quarter the full rows
are kept for the named wallet flows.
"""

import time
from concurrent.futures import ThreadPoolExecutor

import _path  # noqa: F401
from rbnt import config, store
from rbnt.explorer import Explorer

LIMIT = 10000
STEP = 50000


def main():
    cfg = config.load()
    db = store.connect()
    ex = Explorer(cfg, min_interval=0.2)
    q_start, q_end = store.snapshot(db, "start") + 1, store.snapshot(db, "end")
    S = store.SRC

    def pull(a, b):
        rows = ex.internal_range(a, b, offset=LIMIT)
        if len(rows) >= LIMIT:
            if a == b:
                raise SystemExit(f"block {a} alone has {LIMIT}+ internal transfers")
            mid = (a + b) // 2
            return pull(a, mid) + pull(mid + 1, b)
        return rows

    done = store.get_progress(db, "internal") + 1
    t0 = time.time()
    with ThreadPoolExecutor(3) as pool:
        while done <= q_end:
            ranges = [(a, min(a + STEP - 1, q_end)) for a in range(done, min(done + STEP * 6, q_end + 1), STEP)]
            addrs, keep, n = [], [], 0
            for rows in pool.map(lambda r: pull(*r), ranges):
                n += len(rows)
                for r in rows:
                    if r["isError"] != "0":
                        continue
                    if r.get("contractAddress"):
                        addrs.append((r["contractAddress"], S["created"]))
                    if int(r["value"]) > 0:
                        addrs += [(r["from"], S["internal"]), (r["to"], S["internal"])]
                    blk = int(r["blockNumber"])
                    if q_start <= blk <= q_end:
                        to = r["to"] or r.get("contractAddress") or ""
                        keep.append((blk, r["hash"].lower(), r["from"].lower(), to.lower(),
                                     r["value"], r["type"], int(r["isError"]), r.get("traceId", "")))
            store.add_addresses(db, addrs)
            db.executemany("INSERT OR IGNORE INTO internal VALUES (?,?,?,?,?,?,?,?)", keep)
            done = ranges[-1][1] + 1
            store.set_progress(db, "internal", done - 1)
            total = int(store.kv_get(db, "internal_rows", 0)) + n
            store.kv_set(db, "internal_rows", total)
            db.commit()
            print(f"block {done - 1:>9}/{q_end}  internal rows so far {total:,}  {time.time() - t0:,.0f}s", flush=True)


if __name__ == "__main__":
    main()
