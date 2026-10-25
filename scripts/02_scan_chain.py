"""Step 2. Read every block from genesis to the end snapshot.

For every block: the receipts (senders, recipients, created contracts, and the
logs of WRBNT and the two pools) and the header (addresses in extraData, which
is where Redbelly records its governor set). Inside the quarter it also keeps
every transaction with its value and fee.

Resumable: progress is saved after each slice of blocks.
"""

import json
import sys
import time

import _path  # noqa: F401
from rbnt import config, rlp, store
from rbnt.rpc import Rpc

CHUNK = 100       # blocks per batch, the node's batch limit
SLICE = 50        # chunks per commit


def main():
    cfg = config.load()
    db = store.connect()
    rpc = Rpc(cfg["chain"]["rpc_url"], workers=int(sys.argv[1]) if len(sys.argv) > 1 else 24)
    q_start, q_end = store.snapshot(db, "start") + 1, store.snapshot(db, "end")
    watch = {cfg["wrbnt"]["address"].lower(): "wrbnt"}
    watch.update({p["address"].lower(): "pool" for p in cfg["staking_pools"]})
    S = store.SRC

    def fetch(a):
        """Read one batch and keep only what the report needs, inside the worker."""
        nums = range(a, min(a + CHUNK, q_end + 1))
        receipts = rpc.batch([("eth_getBlockReceipts", [hex(n)]) for n in nums])
        heads = rpc.batch([("eth_getBlockByNumber", [hex(n), q_start <= n]) for n in nums])
        out = []
        for n, recs, head in zip(nums, receipts, heads):
            txs = {t["hash"]: t for t in head["transactions"]} if q_start <= n else {}
            slim = []
            for r in recs or []:
                logs = [(lg["transactionHash"], int(lg["logIndex"], 16), lg["address"].lower(), lg["topics"], lg["data"])
                        for lg in r["logs"] if lg["address"].lower() in watch]
                extra = None
                if q_start <= n:
                    t = txs[r["transactionHash"]]
                    extra = (r["transactionHash"], int(r["transactionIndex"], 16), int(r["gasUsed"], 16) *
                             int(r["effectiveGasPrice"], 16), int(t["value"], 16), int(r["status"], 16), t["input"][:10])
                slim.append((r["from"], r["to"], r.get("contractAddress"), logs, extra))
            out.append((n, head["extraData"], int(head["timestamp"], 16), slim))
        return out

    from concurrent.futures import ThreadPoolExecutor
    done = store.get_progress(db, "scan") + 1
    t0, b0 = time.time(), done
    with ThreadPoolExecutor(rpc.workers) as ex:
        while done <= q_end:
            starts = list(range(done, min(done + CHUNK * SLICE, q_end + 1), CHUNK))
            addrs, logs, qtx, qblock, header = [], [], [], [], {}
            for chunk in ex.map(fetch, starts):
                for n, extra_data, ts, slim in chunk:
                    for a in rlp.addresses(extra_data):
                        f, l, c = header.get(a, (n, n, 0))
                        header[a] = (min(f, n), max(l, n), c + 1)
                    fees = 0
                    for frm, to, created, lgs, extra in slim:
                        addrs += [(frm, S["tx_from"]), (to, S["tx_to"]), (created, S["created"])]
                        for txh, li, addr, topics, data in lgs:
                            logs.append((n, txh, li, addr, json.dumps(topics), data))
                            if watch[addr] == "wrbnt":
                                addrs += [("0x" + t[-40:], S["wrbnt_log"]) for t in topics[1:]]
                            elif len(data) >= 66:
                                addrs.append(("0x" + data[26:66], S["pool_log"]))
                        if extra:
                            txh, idx, fee, value, status, input4 = extra
                            fees += fee
                            qtx.append((txh, n, idx, frm.lower(), (to or "").lower(), str(value), str(fee), status,
                                        (created or "").lower(), input4))
                    if q_start <= n:
                        qblock.append((n, ts, str(fees)))
            store.add_addresses(db, addrs)
            store.add_addresses(db, [(a, S["header"]) for a in header])
            for a, (f, l, c) in header.items():
                db.execute("""INSERT INTO header_addr VALUES (?,?,?,?) ON CONFLICT(addr) DO UPDATE SET
                    first_block=min(first_block, excluded.first_block), last_block=max(last_block, excluded.last_block),
                    blocks=blocks+excluded.blocks""", (a, f, l, c))
            db.executemany("INSERT OR IGNORE INTO logs VALUES (?,?,?,?,?,?)", logs)
            db.executemany("INSERT OR IGNORE INTO qtx VALUES (?,?,?,?,?,?,?,?,?,?)", qtx)
            db.executemany("INSERT OR IGNORE INTO qblock VALUES (?,?,?)", qblock)
            done = min(done + CHUNK * SLICE, q_end + 1)
            store.set_progress(db, "scan", done - 1)
            db.commit()
            rate = (done - b0) / (time.time() - t0)
            n_addr = db.execute("SELECT count(*) FROM addresses").fetchone()[0]
            print(f"block {done - 1:>9}/{q_end}  {rate:,.0f} blocks/s  addresses {n_addr:,}"
                  f"  eta {(q_end - done) / rate / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
