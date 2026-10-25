"""Step 4. Public name tags from the explorer.

Reads the explorer's address list, largest first, and keeps the public name
the explorer shows for any address. Only the explorer's own label text is
used. The balances in that list are today's and rounded, so they are never
used for any figure. Also reads the WRBNT holder list to make sure every
WRBNT holder is in the address list.
"""

import _path  # noqa: F401
from rbnt import config, store
from rbnt.explorer import Explorer

MAX_LIST = 20000


def main():
    cfg = config.load()
    db = store.connect()
    ex = Explorer(cfg)
    S = store.SRC
    n, named = 0, 0
    batch, labels = [], []
    for item in ex.v2_paged("addresses", {"sort": "balance,desc", "limit": 200}, max_items=MAX_LIST):
        n += 1
        a = item["address"].lower()
        batch.append((a, S["explorer_list"]))
        if item.get("name"):
            named += 1
            labels.append((a, item["name"], item.get("balance")))
    # Write only after all network reads, so no write lock is held while waiting.
    db.executemany("INSERT OR REPLACE INTO label VALUES (?,?,?)", labels)
    store.add_addresses(db, batch)
    db.commit()
    w = 0
    batch = []
    for item in ex.v2_paged(f"erc20/{cfg['wrbnt']['address']}/holders", {"limit": 200}):
        w += 1
        batch.append((item["address"], S["wrbnt_log"]))
    store.add_addresses(db, batch)
    store.kv_set(db, "explorer_list_read", n)
    store.kv_set(db, "explorer_wrbnt_holders", w)
    db.commit()
    print(f"explorer list: {n} addresses read, {named} with a public name; WRBNT holder list: {w}")
    for a, name in db.execute("SELECT addr, name FROM label"):
        print(f"  label: {name} ({a})")


if __name__ == "__main__":
    main()
