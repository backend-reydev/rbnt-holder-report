"""Step 1. Find the start and end snapshot blocks for the edition.

Uses the Routescan getblocknobytime endpoint (closest=before), then checks the
answer against the RPC: the block must be before the boundary and the next
block must be at or after it. Writes both heights into the edition config.
"""

from datetime import datetime

import _path  # noqa: F401
from rbnt import config
from rbnt.sources import Explorer, Rpc


def unix(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def main():
    cfg = config.load()
    rpc, ex = Rpc(cfg), Explorer(cfg)
    for key, iso in (("start", cfg["period"]["start_utc"]), ("end", cfg["period"]["end_utc"])):
        boundary = unix(iso)
        block = ex.block_before(boundary)
        ts, ts_next = rpc.block_timestamp(block), rpc.block_timestamp(block + 1)
        if not (ts < boundary <= ts_next):
            raise SystemExit(f"{key}: block {block} ({ts}) does not sit just before {iso}")
        cfg["snapshot_blocks"][key] = block
        print(f"{key}: block {block}, timestamp {ts}, boundary {iso}")
    config.save(cfg)


if __name__ == "__main__":
    main()
