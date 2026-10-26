"""Read every internal transfer from genesis to the end snapshot.

Contracts move RBNT through internal calls that have no transaction of their
own, and the public node offers no trace interface, so we read them from the
explorer by block range. A range that comes back full (10,000 rows) is cut in
two until no range is full. Both sides of every successful transfer with value,
and every contract deployed from inside another, join the address list. Rows
inside the quarter are kept whole for the named wallet flows.
"""

import time
from concurrent.futures import ThreadPoolExecutor

from .. import edition, ledger
from ..routescan import Routescan

FULL = 10000
SPAN = 50000


def run(flags):
    cfg = edition.read()
    con = ledger.open_cache()
    explorer = Routescan(cfg, gap_seconds=0.2)
    first_q, last = ledger.block_of(con, "start") + 1, ledger.block_of(con, "end")
    bit = ledger.FOUND_BY

    def rows_between(lo, hi):
        rows = explorer.inner_transfers(lo, hi, FULL)
        if len(rows) < FULL:
            return rows
        if lo == hi:
            raise SystemExit(f"block {lo} alone holds {FULL} or more internal transfers")
        mid = (lo + hi) // 2
        return rows_between(lo, mid) + rows_between(mid + 1, hi)

    lo = ledger.position(con, "traces") + 1
    began = time.time()
    with ThreadPoolExecutor(3) as pool:
        while lo <= last:
            spans = [(a, min(a + SPAN - 1, last)) for a in range(lo, min(lo + SPAN * 6, last + 1), SPAN)]
            found, keep, count = [], [], 0
            for rows in pool.map(lambda s: rows_between(*s), spans):
                count += len(rows)
                for r in rows:
                    if r["isError"] != "0":
                        continue
                    if r.get("contractAddress"):
                        found.append((r["contractAddress"], bit["deployed"]))
                    if int(r["value"]):
                        found += [(r["from"], bit["inner"]), (r["to"], bit["inner"])]
                    height = int(r["blockNumber"])
                    if first_q <= height <= last:
                        to = r["to"] or r.get("contractAddress") or ""
                        keep.append((height, r["hash"].lower(), r["from"].lower(), to.lower(), r["value"], r["type"],
                                     0, r.get("traceId", "")))
            ledger.note_addresses(con, found)
            con.executemany("INSERT OR IGNORE INTO inner_transfers VALUES (?, ?, ?, ?, ?, ?, ?, ?)", keep)
            lo = spans[-1][1] + 1
            ledger.advance(con, "traces", lo - 1)
            ledger.remember(con, "inner_rows", int(ledger.recall(con, "inner_rows", 0)) + count)
            con.commit()
            print(f"  up to block {lo - 1:,} of {last:,}  ({ledger.recall(con, 'inner_rows')} rows, "
                  f"{time.time() - began:,.0f} s)", flush=True)
