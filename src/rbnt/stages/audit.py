"""A second, independent read before anything is published.

Online part: every named wallet's balance, both pools' totalStake and the WRBNT
supply are read again from the node, without the cache, and compared with the
published tables; 600 cached balances picked at random are read again; every
main snapshot block is checked against its moment.
Offline part (also run in CI with --offline): every published file is held to
the house rules in rbnt.rules, and every post of the thread must fit in 280
characters.

The result goes to data/<edition>/audit.json; any failure exits non-zero.
"""

import csv
import json
import random
import re
from datetime import datetime, timezone

from .. import edition, ledger, rules
from ..abi import encode_call
from ..node import Node

WEI = 10 ** 18


def run(flags):
    cfg = edition.read()
    outcome = []

    def note(what, ok, info=""):
        outcome.append({"check": what, "passed": bool(ok), "info": str(info)})
        print(f"  {'ok  ' if ok else 'FAIL'} {what} {info}")

    if "--offline" not in flags:
        node = Node(cfg["chain"]["rpc_url"])
        con = ledger.open_cache()
        start, end = cfg["snapshot_blocks"]["start"], cfg["snapshot_blocks"]["end"]
        folder = edition.out_dir()
        close = lambda live, published: abs(live / WEI - float(published)) < 1e-6
        with open(folder / "named_balances.csv") as fh:
            for row in csv.DictReader(fh):
                for column, height in (("rbnt_start", start), ("rbnt_end", end)):
                    live = int(node.one("eth_getBalance", row["address"], hex(height)), 16)
                    note(f"{row['name']}: {column} read again from the node", close(live, row[column]),
                         f"{live / WEI:,.6f}")
        pool_address = {("Reddex no lock pool" if "no lock" in p["label"] else "Reddex 365 day pool"): p["address"]
                        for p in cfg["staking_pools"]}
        with open(folder / "pools_summary.csv") as fh:
            for row in csv.DictReader(fh):
                for column, height in (("total_stake_start", start), ("total_stake_end", end)):
                    live = int(node.one("eth_call", {"to": pool_address[row["pool"]],
                                                     "data": encode_call("totalStake()")}, hex(height)), 16)
                    note(f"{row['pool']}: {column} read again from the node", close(live, row[column]),
                         f"{live / WEI:,.6f}")
        with open(folder / "supply_reconciliation.csv") as fh:
            rows = list(csv.DictReader(fh))
        for row in (rows[0], rows[-1]):
            live = int(node.one("eth_call", {"to": cfg["wrbnt"]["address"], "data": encode_call("totalSupply()")},
                                hex(int(row["block"]))), 16)
            note(f"WRBNT supply at block {int(row['block']):,} read again from the node",
                 close(live, row["wrbnt_supply"]), f"{live / WEI:,.6f}")
        pool = con.execute("SELECT addr, block, wei FROM native_at WHERE wei != '0' AND block IN (?, ?)",
                           (start, end)).fetchall()
        pick = random.Random(20260930).sample(pool, min(600, len(pool)))
        fresh = node.many([("eth_getBalance", [a, hex(h)]) for a, h, _ in pick])
        differ = sum(int(f, 16) != int(w) for (_, _, w), f in zip(pick, fresh))
        note(f"{len(pick)} cached balances picked at random match a fresh read", differ == 0, f"{differ} differ")
        for label, height, stamp in ledger.moments(con, "main") + ledger.moments(con, "month"):
            cutoff = con.execute("SELECT cutoff FROM moments WHERE label = ?", (label,)).fetchone()[0]
            following = int(node.block(height + 1)["timestamp"], 16)
            note(f"block {height:,} is the newest block before the {label} moment", stamp < cutoff <= following)

    allowed = set(edition.public_names(cfg))
    found = rules.problems_under(edition.HOME, allowed)
    for rule in ("address", "dash", "emoji", "price", "credit"):
        hits = [f for f in found if f["rule"] == rule]
        note(f"published files follow the '{rule}' rule", not hits,
             "; ".join(f"{h['file']}:{h['line']}" for h in hits[:5]))
    thread = edition.HOME / "community" / "thread.txt"
    if thread.exists():
        posts = [p.strip() for p in re.split(r"\n\s*\n", thread.read_text()) if p.strip()]
        too_long = [k + 1 for k, p in enumerate(posts) if len(p) > 280]
        note(f"all {len(posts)} thread posts fit in 280 characters", not too_long, too_long or "")

    failed = [o for o in outcome if not o["passed"]]
    if "--offline" not in flags:
        (edition.out_dir() / "audit.json").write_text(json.dumps(
            {"ran": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "passed": len(outcome) - len(failed),
             "failed": len(failed), "checks": outcome}, indent=2) + "\n")
    print(f"  {len(outcome) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0
