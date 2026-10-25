"""Step 6. What kind of program each RBNT-holding contract is.

For every contract that held at least 1 RBNT (counting WRBNT and stakes) at
any main snapshot, read the contract name from its verified source on the
explorer. The name describes the program, not who controls it, and is only
used to put contracts into broad groups (config: contract_kinds).
"""

import _path  # noqa: F401
from rbnt import config, store
from rbnt.explorer import Explorer

ONE = 10 ** 18


def main():
    cfg = config.load()
    db = store.connect()
    ex = Explorer(cfg)
    contracts = [a for (a,) in db.execute("SELECT addr FROM code WHERE kind='contract'")]
    blocks = [b for _, b, _ in store.snapshots(db, "main")] + [b for _, b, _ in store.snapshots(db, "month")]
    held = {}
    for a, wei in db.execute(f"SELECT addr, wei FROM balance WHERE block IN ({','.join('?' * len(blocks))})", blocks):
        held[a] = max(held.get(a, 0), int(wei))
    for a, wei in db.execute(f"SELECT addr, wei FROM token WHERE block IN ({','.join('?' * len(blocks))})", blocks):
        held[a] = held.get(a, 0) + int(wei)
    todo = [a for a in contracts if held.get(a, 0) >= ONE]
    known = {a for (a,) in db.execute("SELECT addr FROM contract")}
    todo = [a for a in todo if a not in known]
    print(f"{len(todo)} contracts to look up")
    rows = []
    for i, a in enumerate(todo):
        src = ex.source(a)
        name = src.get("ContractName") or ""
        impl = src.get("Implementation") or ""
        if src.get("Proxy") == "1" and impl:
            impl_src = ex.source(impl)
            if impl_src.get("ContractName"):
                name = f"{name} -> {impl_src['ContractName']}" if name else impl_src["ContractName"]
        rows.append((a, name, 1 if name else 0))
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(todo)}", flush=True)
    db.executemany("INSERT OR REPLACE INTO contract VALUES (?,?,?)", rows)
    db.commit()
    names = {}
    for (n,) in db.execute("SELECT name FROM contract"):
        names[n] = names.get(n, 0) + 1
    for n, c in sorted(names.items(), key=lambda x: -x[1]):
        print(f"{c:>5}  {n or '(unverified)'}")


if __name__ == "__main__":
    main()
