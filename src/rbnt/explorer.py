"""Client for the Routescan explorer API (Etherscan compatible and v2)."""

import threading
import time

import requests

_lock = threading.Lock()
_last = [0.0]


class Explorer:
    def __init__(self, cfg, min_interval=0.25):
        self.api = cfg["chain"]["explorer_api"]
        self.v2 = cfg["chain"]["explorer_v2"]
        self.min_interval = min_interval
        self.s = requests.Session()

    def _get(self, url, params=None, retries=8):
        for attempt in range(retries):
            with _lock:
                wait = self.min_interval - (time.time() - _last[0])
                if wait > 0:
                    time.sleep(wait)
                _last[0] = time.time()
            try:
                r = self.s.get(url, params=params, timeout=60)
                if r.status_code == 429:
                    raise requests.RequestException("rate limited")
                r.raise_for_status()
                return r.json()
            except (requests.RequestException, ValueError):
                if attempt == retries - 1:
                    raise
                time.sleep(min(2 ** (attempt + 1), 60))

    def etherscan(self, **params):
        out = self._get(self.api, params)
        if out.get("status") != "1" and "No transactions found" not in str(out.get("message")) \
                and "No records found" not in str(out.get("message")):
            raise RuntimeError(f"explorer {params}: {str(out)[:300]}")
        return out["result"]

    def block_before(self, unix_ts):
        return int(self.etherscan(module="block", action="getblocknobytime",
                                  timestamp=unix_ts, closest="before"))

    def internal_range(self, start, end, page=1, offset=10000):
        return self.etherscan(module="account", action="txlistinternal", startblock=start,
                              endblock=end, page=page, offset=offset, sort="asc")

    def source(self, address):
        return self.etherscan(module="contract", action="getsourcecode", address=address)[0]

    def v2_paged(self, path, params=None, max_items=None):
        url, n = f"{self.v2}/{path}", 0
        while url:
            out = self._get(url, params)
            for item in out.get("items", []):
                yield item
                n += 1
                if max_items and n >= max_items:
                    return
            nxt = out.get("link", {}).get("next")
            url = f"https://api.routescan.io{nxt}" if nxt else None
            params = None
