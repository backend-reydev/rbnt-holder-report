"""Public name tags from the explorer, and its WRBNT holder list.

We page through the explorer's address list from the largest down and keep
the name it shows, word for word, for any address that has one. The balances
in that list are today's and rounded, so no figure in the report uses them.
The WRBNT holder list only makes sure every WRBNT holder gets read later.
"""

from .. import edition, ledger
from ..routescan import Routescan

LIST_DEPTH = 20000


def run(flags):
    cfg = edition.read()
    con = ledger.open_cache()
    explorer = Routescan(cfg)
    bit = ledger.FOUND_BY
    listed, named = [], []
    for item in explorer.walk("addresses", {"sort": "balance,desc", "limit": 200}, cap=LIST_DEPTH):
        listed.append((item["address"], bit["explorer"]))
        if item.get("name"):
            named.append((item["address"].lower(), item["name"], item.get("balance")))
    holders = [(i["address"], bit["wrbnt_event"])
               for i in explorer.walk(f"erc20/{cfg['wrbnt']['address']}/holders", {"limit": 200})]
    # All network reads are done before writing, so no write lock waits on the network.
    con.executemany("INSERT OR REPLACE INTO tags VALUES (?, ?, ?)", named)
    ledger.note_addresses(con, listed + holders)
    ledger.remember(con, "explorer_rows_read", len(listed))
    ledger.remember(con, "explorer_wrbnt_holders_read", len(holders))
    con.commit()
    print(f"  read {len(listed):,} listed addresses, {len(named)} with a name tag; {len(holders):,} WRBNT holders")
    for addr, name, _ in named:
        print(f"  tag: {name}")
