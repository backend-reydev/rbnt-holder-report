"""Step 5. Read every balance the report needs, straight from the node.

At the four main snapshots (quarter start, each month end, quarter end):
  * native RBNT of every address that could hold any (eth_getBalance)
  * WRBNT balanceOf of every address that ever touched WRBNT, and totalSupply
  * userInfo(address).amount in each pool for every address that ever staked,
    and each pool's totalStake
Every day of the quarter: the native balance of each named wallet, the WRBNT
supply and each pool's balance and totalStake.
At the end: the open stakes and unlock times in each pool (lock calendar), and
eth_getCode for every address that held anything, to tell wallets from
contracts.
"""

import time

import _path  # noqa: F401
from rbnt import config, store
from rbnt.rpc import Rpc, call_data, words

MAIN = ["start", "month_2026-08-01", "month_2026-09-01", "end"]


def progress(label):
    t0 = time.time()

    def f(done, total):
        print(f"  {label}: {done}/{total} batches  {time.time() - t0:,.0f}s", flush=True)
    return f


def main():
    cfg = config.load()
    db = store.connect()
    rpc = Rpc(cfg["chain"]["rpc_url"], workers=24)
    wrbnt = cfg["wrbnt"]["address"].lower()
    pools = [p["address"].lower() for p in cfg["staking_pools"]]
    named = list(config.named_wallets(cfg))
    store.add_addresses(db, [(a, store.SRC["named"]) for a in named])
    db.commit()
    blocks = {name: store.snapshot(db, name) for name in MAIN}
    q0, q1 = blocks["start"] + 1, blocks["end"]

    def have(block):
        return {a for (a,) in db.execute("SELECT addr FROM balance WHERE block=?", (block,))}

    def save_native(addrs, block, label):
        addrs = sorted(set(addrs) - have(block))
        if not addrs:
            return
        print(f"{label}: {len(addrs):,} addresses at block {block}", flush=True)
        for i in range(0, len(addrs), 50000):
            part = addrs[i:i + 50000]
            vals = rpc.balances(part, block)
            db.executemany("INSERT OR REPLACE INTO balance VALUES (?,?,?)", zip(part, [block] * len(part), map(str, vals)))
            db.commit()

    # Native balances: everyone at start and end.
    every = [a for (a,) in db.execute("SELECT addr FROM addresses")]
    save_native(every, blocks["start"], "native start")
    save_native(every, blocks["end"], "native end")
    # Month ends: anyone non-zero at start or end, or active in the quarter.
    active = {a for (a,) in db.execute(
        "SELECT addr FROM balance WHERE block IN (?,?) AND wei != '0'", (blocks["start"], blocks["end"]))}
    for col in ("sender", "recipient"):
        active |= {a for (a,) in db.execute(f"SELECT DISTINCT {col} FROM qtx WHERE {col} != ''")}
        active |= {a for (a,) in db.execute(f"SELECT DISTINCT {col} FROM internal WHERE {col} != ''")}
    active |= {a for (a,) in db.execute("SELECT addr FROM header_addr WHERE last_block >= ?", (q0,))}
    active |= set(named)
    for name in MAIN[1:3]:
        save_native(active, blocks[name], f"native {name}")
    # Daily: named wallets.
    for name, block, _ in store.snapshots(db, "day") + store.snapshots(db, "week"):
        save_native(named, block, f"named {name}")

    # WRBNT balances and supply.
    holders = sorted(a for (a,) in db.execute("SELECT addr FROM addresses WHERE src & ?", (store.SRC["wrbnt_log"],)))
    for name, block in blocks.items():
        done = {a for (a,) in db.execute("SELECT addr FROM token WHERE block=? AND kind='wrbnt'", (block,))}
        todo = [a for a in holders if a not in done]
        if todo:
            res = rpc.eth_calls(wrbnt, [call_data("balanceOf(address)", a) for a in todo], block)
            db.executemany("INSERT OR REPLACE INTO token VALUES (?,?,?,?)",
                           [(a, block, "wrbnt", str(int(r, 16))) for a, r in zip(todo, res)])
            db.commit()
        print(f"WRBNT balances at {name}: {len(holders):,} holders", flush=True)

    # Pool stakes.
    stakers = sorted(a for (a,) in db.execute("SELECT addr FROM addresses WHERE src & ?", (store.SRC["pool_log"],)))
    for pool in pools:
        for name, block in blocks.items():
            kind = f"stake:{pool}"
            done = {a for (a,) in db.execute("SELECT addr FROM token WHERE block=? AND kind=?", (block, kind))}
            todo = [a for a in stakers if a not in done]
            if todo:
                res = rpc.eth_calls(pool, [call_data("userInfo(address)", a) for a in todo], block)
                db.executemany("INSERT OR REPLACE INTO token VALUES (?,?,?,?)",
                               [(a, block, kind, str(words(r)[0])) for a, r in zip(todo, res)])
                db.commit()
        print(f"stakes read for pool {pool}: {len(stakers):,} candidate stakers", flush=True)

    # Contract level figures at every snapshot (main, weekly, daily).
    every_snap = sorted({b for _, b, _ in store.snapshots(db)})
    calls, keys = [], []
    for b in every_snap:
        calls.append(("eth_call", [{"to": wrbnt, "data": call_data("totalSupply()")}, hex(b)]))
        keys.append(("wrbnt_supply", b))
        for pool in pools:
            calls.append(("eth_call", [{"to": pool, "data": call_data("totalStake()")}, hex(b)]))
            keys.append((f"total_stake:{pool}", b))
            calls.append(("eth_getBalance", [pool, hex(b)]))
            keys.append((f"pool_balance:{pool}", b))
        calls.append(("eth_getBalance", [wrbnt, hex(b)]))
        keys.append(("wrbnt_balance", b))
    for (k, b), r in zip(keys, rpc.map(calls)):
        store.kv_set(db, f"{k}@{b}", int(r, 16))
    db.commit()
    print(f"contract figures at {len(every_snap)} snapshots", flush=True)

    # Lock calendar at the end: every open stake and when it unlocks.
    db.execute("DELETE FROM unlocks")
    for pool in pools:
        kind = f"stake:{pool}"
        open_ = [a for (a,) in db.execute("SELECT addr FROM token WHERE block=? AND kind=? AND wei != '0'",
                                          (blocks["end"], kind))]
        res = rpc.eth_calls(pool, [call_data("getStakeUnlockTimes(address)", a) for a in open_], blocks["end"])
        rows = []
        for a, r in zip(open_, res):
            w = words(r)
            n = w[2]                       # length of the amounts array
            amounts = w[3:3 + n]
            times = w[3 + n + 1:3 + n + 1 + n]
            rows += [(pool, a, str(am), t) for am, t in zip(amounts, times)]
        db.executemany("INSERT INTO unlocks VALUES (?,?,?,?)", rows)
        db.commit()
        print(f"lock calendar for {pool}: {len(rows):,} open stakes", flush=True)

    # Wallet or contract, at the end block, for every address that held anything.
    holders_any = {a for (a,) in db.execute("SELECT addr FROM balance WHERE wei != '0'")}
    holders_any |= {a for (a,) in db.execute("SELECT addr FROM token WHERE wei != '0'")}
    todo = sorted(holders_any - {a for (a,) in db.execute("SELECT addr FROM code")})
    res = rpc.map([("eth_getCode", [a, hex(blocks["end"])]) for a in todo], progress("code"))
    rows = []
    for a, c in zip(todo, res):
        if c in ("0x", "0x0"):
            kind = "wallet"
        elif c.startswith("0xef0100") and len(c) == 2 + 46:
            kind = "delegated"          # EIP-7702 delegation marker: still a key-held wallet
        else:
            kind = "contract"
        rows.append((a, kind))
    db.executemany("INSERT OR REPLACE INTO code VALUES (?,?)", rows)
    db.commit()
    print(f"code read for {len(todo):,} addresses", flush=True)


if __name__ == "__main__":
    main()
