"""Clients for the Redbelly RPC and the Routescan explorer API.

Every request is written to data/raw/<edition>/provenance.csv with the source,
the query and the UTC time it was made, so each figure in the report can be
traced back to the call that produced it.
"""

import csv
import time
from datetime import datetime, timezone
from decimal import Decimal

import requests

from . import config

WEI = Decimal(10) ** 18
_session = requests.Session()


def to_rbnt(wei):
    return Decimal(int(wei)) / WEI


def _log(source, query, result):
    path = config.data_dir("raw") / "provenance.csv"
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["fetched_utc", "source", "query", "result"])
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        w.writerow([stamp, source, query, str(result)[:200]])


def _get(url, params, retries=4):
    for attempt in range(retries):
        try:
            r = _session.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))


class Rpc:
    def __init__(self, cfg):
        self.url = cfg["chain"]["rpc_url"]

    def call(self, method, params):
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        r = _session.post(self.url, json=body, timeout=30)
        r.raise_for_status()
        out = r.json()
        if "error" in out:
            raise RuntimeError(f"{method} {params}: {out['error']}")
        _log("rpc", f"{method} {params}", out["result"])
        return out["result"]

    def balance(self, address, block):
        """Native RBNT balance in wei at a block height."""
        return int(self.call("eth_getBalance", [address, hex(block)]), 16)

    def block_timestamp(self, block):
        b = self.call("eth_getBlockByNumber", [hex(block), False])
        return int(b["timestamp"], 16)


class Explorer:
    def __init__(self, cfg):
        self.api = cfg["chain"]["explorer_api"]
        self.v2 = cfg["chain"]["explorer_v2"]

    def etherscan(self, **params):
        out = _get(self.api, params)
        if out.get("status") != "1" and out.get("message") != "No transactions found":
            raise RuntimeError(f"explorer {params}: {out}")
        _log("routescan-etherscan", params, out.get("result"))
        return out["result"]

    def block_before(self, unix_ts):
        return int(self.etherscan(module="block", action="getblocknobytime",
                                  timestamp=unix_ts, closest="before"))

    def v2_paged(self, path, limit=100, max_pages=None):
        """Walk a Routescan v2 list endpoint that returns items plus link.next."""
        url, params, page = f"{self.v2}/{path}", {"limit": limit}, 0
        while url:
            out = _get(url, params)
            _log("routescan-v2", url, f"{len(out.get('items', []))} items")
            yield from out.get("items", [])
            nxt = out.get("link", {}).get("next")
            url = f"https://api.routescan.io{nxt}" if nxt else None
            params, page = None, page + 1
            if max_pages and page >= max_pages:
                break
