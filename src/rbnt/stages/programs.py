"""What kind of program each RBNT-holding contract is.

For every contract that held at least 1 RBNT (wrapped and staked included) at
a main moment, we read the contract name from its verified source on the
explorer; for a proxy, the name of the program behind it. The name describes
the program, never who runs it, and is only used to sort contracts into broad
kinds (config: contract_kinds).
"""

from collections import Counter

from .. import edition, ledger
from ..routescan import Routescan

ONE = 10 ** 18


def run(flags):
    cfg = edition.read()
    con = ledger.open_cache()
    explorer = Routescan(cfg)
    contracts = [a for (a,) in con.execute("SELECT addr FROM bytecode_kind WHERE kind = 'contract'")]
    heights = [h for _, h, _ in ledger.moments(con, "main") + ledger.moments(con, "month")]
    marks = ",".join("?" * len(heights))
    peak = Counter()
    for a, w in con.execute(f"SELECT addr, wei FROM native_at WHERE block IN ({marks})", heights):
        peak[a] = max(peak[a], int(w))
    for a, w in con.execute(f"SELECT addr, wei FROM token_at WHERE block IN ({marks})", heights):
        peak[a] += int(w)
    known = {a for (a,) in con.execute("SELECT addr FROM program_name")}
    todo = [a for a in contracts if peak[a] >= ONE and a not in known]
    print(f"  {len(todo)} contracts to look up")
    rows = []
    for a in todo:
        src = explorer.verified_source(a)
        name = src.get("ContractName") or ""
        if src.get("Proxy") == "1" and src.get("Implementation"):
            behind = explorer.verified_source(src["Implementation"]).get("ContractName")
            if behind:
                name = f"{name} -> {behind}" if name else behind
        rows.append((a, name, int(bool(name))))
    con.executemany("INSERT OR REPLACE INTO program_name VALUES (?, ?, ?)", rows)
    con.commit()
    for name, count in Counter(n for (n,) in con.execute("SELECT name FROM program_name")).most_common():
        print(f"  {count:>4}  {name or '(no verified source)'}")
