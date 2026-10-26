"""Read every balance the report uses, straight from the node.

At the four main moments (quarter start, both month ends, quarter end):
  native RBNT of every address that could hold any; WRBNT balanceOf of every
  address that ever touched WRBNT; each pool's userInfo(address).amount for
  every address that ever staked.
At every moment (daily, weekly, main): WRBNT totalSupply and the WRBNT
  contract's RBNT, each pool's totalStake and RBNT, each named wallet's RBNT.
At the quarter end: the open stakes and unlock times in each pool, and the
  bytecode of every address that held anything (wallet or contract).
Anything already read is skipped, so the stage can be run again safely.
"""

from .. import edition, ledger
from ..abi import encode_call, unpack_words
from ..node import Node

MAIN = ["start", "month_2026-08-01", "month_2026-09-01", "end"]


def run(flags):
    cfg = edition.read()
    con = ledger.open_cache()
    node = Node(cfg["chain"]["rpc_url"])
    wrbnt = cfg["wrbnt"]["address"].lower()
    pools = [p["address"].lower() for p in cfg["staking_pools"]]
    names = list(edition.public_names(cfg))
    ledger.note_addresses(con, [(a, ledger.FOUND_BY["named"]) for a in names])
    con.commit()
    main = {label: ledger.block_of(con, label) for label in MAIN}

    def already(height):
        return {a for (a,) in con.execute("SELECT addr FROM native_at WHERE block = ?", (height,))}

    def native(addresses, height, why):
        todo = sorted(set(addresses) - already(height))
        if todo:
            print(f"  {why}: {len(todo):,} addresses at block {height:,}", flush=True)
        for k in range(0, len(todo), 50000):
            part = todo[k:k + 50000]
            con.executemany("INSERT OR REPLACE INTO native_at VALUES (?, ?, ?)",
                            [(a, height, str(v)) for a, v in zip(part, node.balances_at(part, height))])
            con.commit()

    everyone = [a for (a,) in con.execute("SELECT addr FROM seen")]
    native(everyone, main["start"], "RBNT at the start")
    native(everyone, main["end"], "RBNT at the end")
    # An address that was empty at both ends and never moved in the quarter cannot hold anything at a month end.
    moving = {a for (a,) in con.execute("SELECT addr FROM native_at WHERE block IN (?, ?) AND wei != '0'",
                                        (main["start"], main["end"]))}
    for col in ("sender", "recipient"):
        for table in ("quarter_tx", "inner_transfers"):
            moving |= {a for (a,) in con.execute(f"SELECT DISTINCT {col} FROM {table} WHERE {col} != ''")}
    moving |= {a for (a,) in con.execute("SELECT addr FROM header_seen WHERE last_block > ?", (main["start"],))}
    moving |= set(names)
    for label in MAIN[1:3]:
        native(moving, main[label], f"RBNT at {label}")
    for label, height, _ in ledger.moments(con, "day") + ledger.moments(con, "week"):
        native(names, height, f"named wallets on {label}")

    def token_reads(kind, contract, holders, signature, pick):
        for label, height in main.items():
            done = {a for (a,) in con.execute("SELECT addr FROM token_at WHERE block = ? AND kind = ?", (height, kind))}
            todo = [a for a in holders if a not in done]
            if todo:
                answers = node.calls_at(contract, [encode_call(signature, a) for a in todo], height)
                con.executemany("INSERT OR REPLACE INTO token_at VALUES (?, ?, ?, ?)",
                                [(a, height, kind, str(pick(r))) for a, r in zip(todo, answers)])
                con.commit()

    wrbnt_holders = sorted(a for (a,) in con.execute("SELECT addr FROM seen WHERE how & ?",
                                                     (ledger.FOUND_BY["wrbnt_event"],)))
    token_reads("wrbnt", wrbnt, wrbnt_holders, "balanceOf(address)", lambda r: int(r, 16))
    print(f"  WRBNT balances of {len(wrbnt_holders):,} addresses at {len(main)} moments", flush=True)
    stakers = sorted(a for (a,) in con.execute("SELECT addr FROM seen WHERE how & ?", (ledger.FOUND_BY["pool_event"],)))
    for pool in pools:
        token_reads(f"stake:{pool}", pool, stakers, "userInfo(address)", lambda r: unpack_words(r)[0])
    print(f"  pool stakes of {len(stakers):,} addresses at {len(main)} moments", flush=True)

    heights = sorted({h for _, h, _ in con.execute("SELECT label, block, ts FROM moments")})
    asks, keys = [], []
    for h in heights:
        asks += [("eth_call", [{"to": wrbnt, "data": encode_call("totalSupply()")}, hex(h)]),
                 ("eth_getBalance", [wrbnt, hex(h)])]
        keys += [f"wrbnt_supply@{h}", f"wrbnt_balance@{h}"]
        for pool in pools:
            asks += [("eth_call", [{"to": pool, "data": encode_call("totalStake()")}, hex(h)]),
                     ("eth_getBalance", [pool, hex(h)])]
            keys += [f"total_stake:{pool}@{h}", f"pool_balance:{pool}@{h}"]
    for key, answer in zip(keys, node.many(asks)):
        ledger.remember(con, key, int(answer, 16))
    con.commit()
    print(f"  contract totals at {len(heights)} blocks", flush=True)

    con.execute("DELETE FROM locks")
    for pool in pools:
        open_ = [a for (a,) in con.execute("SELECT addr FROM token_at WHERE block = ? AND kind = ? AND wei != '0'",
                                           (main["end"], f"stake:{pool}"))]
        answers = node.calls_at(pool, [encode_call("getStakeUnlockTimes(address)", a) for a in open_], main["end"])
        rows = []
        for a, r in zip(open_, answers):
            w = unpack_words(r)            # [offset, offset, n, amounts..., n, times...]
            n = w[2]
            rows += [(pool, a, str(amount), when) for amount, when in zip(w[3:3 + n], w[4 + n:4 + 2 * n])]
        con.executemany("INSERT INTO locks VALUES (?, ?, ?, ?)", rows)
        con.commit()
        print(f"  {len(rows):,} open stakes in {pool}", flush=True)

    holders = {a for (a,) in con.execute("SELECT addr FROM native_at WHERE wei != '0'")}
    holders |= {a for (a,) in con.execute("SELECT addr FROM token_at WHERE wei != '0'")}
    todo = sorted(holders - {a for (a,) in con.execute("SELECT addr FROM bytecode_kind")})
    codes = node.many([("eth_getCode", [a, hex(main["end"])]) for a in todo])

    def kind(code):
        if code in ("0x", "0x0"):
            return "wallet"
        if code.startswith("0xef0100") and len(code) == 48:   # EIP-7702 delegation: still a key-held wallet
            return "delegated"
        return "contract"
    con.executemany("INSERT OR REPLACE INTO bytecode_kind VALUES (?, ?)", [(a, kind(c)) for a, c in zip(todo, codes)])
    con.commit()
    print(f"  bytecode checked for {len(todo):,} addresses", flush=True)
