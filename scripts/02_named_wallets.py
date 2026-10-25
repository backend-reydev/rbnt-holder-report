"""Step 2. Balances of every publicly named wallet at both snapshots.

Covers Redbelly's reserved wallets, the Wrapped RBNT contract, the two Reddex
staking pools and any explorer labelled contracts in the config. Output:
data/processed/<edition>/named_wallets.csv
"""

import csv

import _path  # noqa: F401
from rbnt import config
from rbnt.sources import Rpc, to_rbnt


def rows(cfg):
    yield "Wrapped RBNT", cfg["wrbnt"]["label"], cfg["wrbnt"]["address"]
    for p in cfg["staking_pools"]:
        yield "Staking pool", p["label"], p["address"]
    for w in cfg["reserved_wallets"]["wallets"]:
        yield "Reserved wallet", w["label"], w["address"]
    for w in cfg["labelled_contracts"]["wallets"]:
        yield w.get("category", "Labelled contract"), w["label"], w["address"]


def main():
    cfg = config.load()
    start, end = cfg["snapshot_blocks"]["start"], cfg["snapshot_blocks"]["end"]
    if not (start and end):
        raise SystemExit("Run scripts/01_snapshot_blocks.py first.")
    rpc = Rpc(cfg)
    out = config.data_dir("processed") / "named_wallets.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category", "label", "address", f"balance_block_{start}",
                    f"balance_block_{end}", "change_rbnt", "source"])
        for category, label, address in rows(cfg):
            b0, b1 = to_rbnt(rpc.balance(address, start)), to_rbnt(rpc.balance(address, end))
            w.writerow([category, label, address, f"{b0:.6f}", f"{b1:.6f}",
                        f"{b1 - b0:.6f}", "eth_getBalance via Redbelly mainnet RPC"])
            print(f"{label:45} {b0:>22,.2f} -> {b1:>22,.2f}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
