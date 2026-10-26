"""Read every block from genesis to the end snapshot.

From each block's receipts we keep who sent, who received and which contract
was deployed, plus every event emitted by WRBNT or either pool. From each
header we keep the 20-byte values in extraData (the governor set, which is paid
the fees). Inside the quarter we also keep every transaction with its value
and fee. Progress is saved every few thousand blocks.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor

from .. import edition, ledger, rlp
from ..node import Node

STEP = 100          # blocks per request batch
SAVE_EVERY = 50     # batches between saves


def run(flags):
    cfg = edition.read()
    con = ledger.open_cache()
    node = Node(cfg["chain"]["rpc_url"])
    first_q, last = ledger.block_of(con, "start") + 1, ledger.block_of(con, "end")
    watched = {cfg["wrbnt"]["address"].lower(): "wrbnt"}
    watched.update({p["address"].lower(): "pool" for p in cfg["staking_pools"]})
    bit = ledger.FOUND_BY

    def read_batch(lo):
        heights = range(lo, min(lo + STEP, last + 1))
        receipts = node.send([("eth_getBlockReceipts", [hex(h)]) for h in heights])
        headers = node.send([("eth_getBlockByNumber", [hex(h), h >= first_q]) for h in heights])
        kept = []
        for h, recs, head in zip(heights, receipts, headers):
            values = {t["hash"]: int(t["value"], 16) for t in head["transactions"]} if h >= first_q else {}
            rows = []
            for r in recs or []:
                events = [(e["transactionHash"], int(e["logIndex"], 16), e["address"].lower(), e["topics"], e["data"])
                          for e in r["logs"] if e["address"].lower() in watched]
                quarter = None
                if h >= first_q:
                    fee = int(r["gasUsed"], 16) * int(r["effectiveGasPrice"], 16)
                    quarter = (r["transactionHash"], int(r["transactionIndex"], 16), fee,
                               values[r["transactionHash"]], int(r["status"], 16))
                rows.append((r["from"], r["to"], r.get("contractAddress"), events, quarter))
            inputs = {t["hash"]: t["input"][:10] for t in head["transactions"]} if h >= first_q else {}
            kept.append((h, head["extraData"], int(head["timestamp"], 16), rows, inputs))
        return kept

    lo = ledger.position(con, "crawl") + 1
    began, began_at = time.time(), lo
    with ThreadPoolExecutor(node.threads) as pool:
        while lo <= last:
            starts = list(range(lo, min(lo + STEP * SAVE_EVERY, last + 1), STEP))
            found, logs, txs, blocks, governors = [], [], [], [], {}
            for batch in pool.map(read_batch, starts):
                for h, extra, ts, rows, inputs in batch:
                    for g in rlp.twenty_byte_values(extra):
                        f, l, c = governors.get(g, (h, h, 0))
                        governors[g] = (min(f, h), max(l, h), c + 1)
                    fees = 0
                    for sender, recipient, deployed, events, quarter in rows:
                        found += [(sender, bit["sender"]), (recipient, bit["recipient"]), (deployed, bit["deployed"])]
                        for txh, li, where, topics, data in events:
                            logs.append((h, txh, li, where, json.dumps(topics), data))
                            if watched[where] == "wrbnt":
                                found += [("0x" + t[-40:], bit["wrbnt_event"]) for t in topics[1:]]
                            elif len(data) >= 66:
                                found.append(("0x" + data[26:66], bit["pool_event"]))
                        if quarter:
                            txh, idx, fee, value, status = quarter
                            fees += fee
                            txs.append((txh, h, idx, sender.lower(), (recipient or "").lower(), str(value), str(fee),
                                        status, (deployed or "").lower(), inputs.get(txh, "")))
                    if h >= first_q:
                        blocks.append((h, ts, str(fees)))
            ledger.note_addresses(con, found)
            ledger.note_addresses(con, [(g, bit["header"]) for g in governors])
            con.executemany("""INSERT INTO header_seen VALUES (?, ?, ?, ?) ON CONFLICT(addr) DO UPDATE SET
                first_block = min(first_block, excluded.first_block), last_block = max(last_block, excluded.last_block),
                blocks = blocks + excluded.blocks""", [(g, f, l, c) for g, (f, l, c) in governors.items()])
            con.executemany("INSERT OR IGNORE INTO watched_logs VALUES (?, ?, ?, ?, ?, ?)", logs)
            con.executemany("INSERT OR IGNORE INTO quarter_tx VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", txs)
            con.executemany("INSERT OR IGNORE INTO quarter_block VALUES (?, ?, ?)", blocks)
            lo = min(lo + STEP * SAVE_EVERY, last + 1)
            ledger.advance(con, "crawl", lo - 1)
            con.commit()
            speed = (lo - began_at) / max(time.time() - began, 1e-9)
            total = con.execute("SELECT count(*) FROM seen").fetchone()[0]
            print(f"  up to block {lo - 1:,} of {last:,}  ({speed:,.0f} blocks a second, {total:,} addresses)", flush=True)
