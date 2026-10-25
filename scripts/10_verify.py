"""Step 10. Independent checks before anything is published.

1. Re-reads every headline figure straight from the node, without the cache,
   and compares it with the published CSVs.
2. Re-reads a random sample of cached balances from the node.
3. Re-checks every main snapshot boundary.
4. Scans every published file for addresses outside the named list, em or en
   dashes, emoji, price talk and personal credit lines.
5. Checks every post in the X thread fits in 280 characters.

Writes data/processed/<edition>/verification.json and exits non-zero if any
check fails. `--offline` runs only checks 4 and 5 (used in CI).
"""

import csv
import json
import random
import sys
from datetime import datetime, timezone

import _path  # noqa: F401
from rbnt import config
from rbnt.publish_rules import scan_tree

WEI = 10 ** 18
RESULTS = []


def result(name, ok, detail=""):
    RESULTS.append({"check": name, "passed": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def online_checks(cfg):
    from rbnt import store
    from rbnt.rpc import Rpc, call_data
    rpc = Rpc(cfg["chain"]["rpc_url"])
    db = store.connect()
    proc = config.data_dir("processed")
    s0, s1 = cfg["snapshot_blocks"]["start"], cfg["snapshot_blocks"]["end"]

    # 1. Headline figures, fresh from the node.
    with open(proc / "08_named_wallets.csv") as f:
        for row in csv.DictReader(f):
            for col, blk in (("balance_start", s0), ("balance_end", s1)):
                live = int(rpc.call("eth_getBalance", [row["address"], hex(blk)]), 16)
                result(f"{row['label']} {col} matches the node", abs(live / WEI - float(row[col])) < 1e-6,
                       f"{live / WEI:,.6f}")
    with open(proc / "07_staking_pools.csv") as f:
        pools = {p["label"]: p["address"] for p in cfg["staking_pools"]}
        for row in csv.DictReader(f):
            addr = pools[row["pool"]]
            for col, blk in (("total_stake_start", s0), ("total_stake_end", s1)):
                live = int(rpc.call("eth_call", [{"to": addr, "data": call_data("totalStake()")}, hex(blk)]), 16)
                result(f"{row['pool']} {col} matches the node", abs(live / WEI - float(row[col])) < 1e-6,
                       f"{live / WEI:,.6f}")
    with open(proc / "01_supply_check.csv") as f:
        rows = list(csv.DictReader(f))
    for row in (rows[0], rows[-1]):
        blk = int(row["block"])
        live = int(rpc.call("eth_call", [{"to": cfg["wrbnt"]["address"], "data": call_data("totalSupply()")}, hex(blk)]), 16)
        result(f"WRBNT supply at block {blk} matches the node", abs(live / WEI - float(row["wrbnt_supply"])) < 1e-6,
               f"{live / WEI:,.6f}")

    # 2. Random sample of cached balances.
    rows = db.execute("SELECT addr, block, wei FROM balance WHERE wei != '0' AND block IN (?, ?)", (s0, s1)).fetchall()
    random.seed(151)
    sample = random.sample(rows, min(600, len(rows)))
    live = rpc.map([("eth_getBalance", [a, hex(b)]) for a, b, _ in sample])
    bad = sum(1 for (_, _, w), l in zip(sample, live) if int(l, 16) != int(w))
    result(f"{len(sample)} random cached balances match the node", bad == 0, f"{bad} differ")

    # 3. Snapshot boundaries.
    for name, block, ts in store.snapshots(db, "main") + store.snapshots(db, "month"):
        nxt = int(rpc.block(block + 1)["timestamp"], 16)
        boundary = db.execute("SELECT boundary FROM snapshots WHERE name=?", (name,)).fetchone()[0]
        result(f"Snapshot {name} is the last block before its boundary", ts < boundary <= nxt, f"block {block}")


def offline_checks(cfg):
    named = set(config.named_wallets(cfg))
    problems = scan_tree(config.ROOT, named)
    for kind in ("address", "dash", "emoji", "price", "credit"):
        hits = [p for p in problems if p["kind"] == kind]
        result(f"No {kind} problems in published files", not hits, "; ".join(f"{h['file']}:{h['line']}" for h in hits[:5]))
    thread = config.ROOT / "community" / "x_thread.txt"
    if thread.exists():
        posts = [p.strip() for p in thread.read_text().split("\n---\n") if p.strip()]
        long_ = [i + 1 for i, p in enumerate(posts) if len(p) > 280]
        result(f"All {len(posts)} X posts fit in 280 characters", not long_, f"too long: {long_}" if long_ else "")


def main():
    cfg = config.load()
    offline = "--offline" in sys.argv
    if not offline:
        online_checks(cfg)
    offline_checks(cfg)
    failed = [r for r in RESULTS if not r["passed"]]
    if not offline:
        out = config.data_dir("processed") / "verification.json"
        out.write_text(json.dumps({"verified_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                                   "passed": len(RESULTS) - len(failed), "failed": len(failed),
                                   "results": RESULTS}, indent=2) + "\n")
    print(f"\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
