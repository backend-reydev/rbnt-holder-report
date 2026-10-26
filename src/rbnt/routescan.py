"""Routescan, the Redbelly explorer: its Etherscan style API and its v2 lists.

Requests are spaced out across threads so the free tier is never hammered, and
a refused or failed request is tried again after a growing pause.
"""

import threading
import time

import requests

_gate = threading.Lock()
_last_call = [0.0]


class Routescan:
    def __init__(self, cfg, gap_seconds=0.25):
        self.classic = cfg["chain"]["explorer_api"]
        self.v2 = cfg["chain"]["explorer_v2"]
        self.gap = gap_seconds
        self.http = requests.Session()

    def _fetch(self, url, params=None, tries=8):
        for attempt in range(tries):
            with _gate:
                pause = self.gap - (time.monotonic() - _last_call[0])
                if pause > 0:
                    time.sleep(pause)
                _last_call[0] = time.monotonic()
            try:
                reply = self.http.get(url, params=params, timeout=60)
                if reply.status_code == 429:
                    raise requests.RequestException("too many requests")
                reply.raise_for_status()
                return reply.json()
            except (requests.RequestException, ValueError):
                if attempt + 1 == tries:
                    raise
                time.sleep(min(60, 2 * (attempt + 1) ** 2))

    def api(self, **params):
        body = self._fetch(self.classic, params)
        empty = any(w in str(body.get("message")) for w in ("No transactions found", "No records found"))
        if body.get("status") != "1" and not empty:
            raise RuntimeError(f"explorer refused {params}: {str(body)[:300]}")
        return body["result"]

    def block_before(self, unix_time):
        return int(self.api(module="block", action="getblocknobytime", timestamp=unix_time, closest="before"))

    def inner_transfers(self, first_block, last_block, limit=10000):
        return self.api(module="account", action="txlistinternal", startblock=first_block, endblock=last_block,
                        page=1, offset=limit, sort="asc")

    def verified_source(self, address):
        return self.api(module="contract", action="getsourcecode", address=address)[0]

    def walk(self, path, params=None, cap=None):
        """Yield items from a v2 list, following its link.next pages."""
        url, count = f"{self.v2}/{path}", 0
        while url:
            page = self._fetch(url, params)
            for item in page.get("items", []):
                yield item
                count += 1
                if cap and count >= cap:
                    return
            nxt = (page.get("link") or {}).get("next")
            url, params = (f"https://api.routescan.io{nxt}" if nxt else None), None
