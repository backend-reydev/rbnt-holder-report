"""Batched, concurrent JSON-RPC client for the Redbelly mainnet node.

The public node accepts batches of up to 100 calls. map() splits any list of
calls into batches, runs them on a thread pool and returns results in order.
Failed batches are retried with backoff, then split in half, so one bad call
never hides the rest.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

MAX_BATCH = 100


class RpcError(RuntimeError):
    pass


class TooLarge(RpcError):
    """The node refuses a batch whose response is too big. Split, do not wait."""


class Rpc:
    def __init__(self, url, workers=16):
        self.url = url
        self.workers = workers
        self._local = threading.local()

    def _session(self):
        if not hasattr(self._local, "s"):
            self._local.s = requests.Session()
        return self._local.s

    def call(self, method, params):
        return self.batch([(method, params)])[0]

    def batch(self, calls, retries=6):
        body = [{"jsonrpc": "2.0", "id": i, "method": m, "params": p}
                for i, (m, p) in enumerate(calls)]
        last = None
        for attempt in range(retries):
            try:
                r = self._session().post(self.url, json=body, timeout=120)
                r.raise_for_status()
                out = r.json()
                if isinstance(out, dict):
                    raise RpcError(out.get("error"))
                out.sort(key=lambda x: x["id"])
                errors = [x for x in out if "error" in x]
                if any("too large" in str(x["error"].get("message", "")) for x in errors) and len(calls) > 1:
                    raise TooLarge(errors[0]["error"])
                if errors:
                    raise RpcError(errors[0]["error"])
                return [x["result"] for x in out]
            except TooLarge:
                break
            except (requests.RequestException, RpcError, ValueError) as e:
                last = e
                time.sleep(min(2 ** attempt, 30))
        if len(calls) > 1:
            mid = len(calls) // 2
            return self.batch(calls[:mid], retries) + self.batch(calls[mid:], retries)
        raise RpcError(f"{calls[0]}: {last}")

    def map(self, calls, progress=None):
        chunks = [calls[i:i + MAX_BATCH] for i in range(0, len(calls), MAX_BATCH)]
        results = [None] * len(chunks)
        done = 0
        with ThreadPoolExecutor(self.workers) as ex:
            futures = {ex.submit(self.batch, c): i for i, c in enumerate(chunks)}
            for f in futures:
                results[futures[f]] = f.result()
                done += 1
                if progress and done % 200 == 0:
                    progress(done, len(chunks))
        return [x for chunk in results for x in chunk]

    # Typed helpers -------------------------------------------------------

    def block(self, number, full=False):
        return self.call("eth_getBlockByNumber", [hex(number), full])

    def balances(self, addresses, block):
        res = self.map([("eth_getBalance", [a, hex(block)]) for a in addresses])
        return [int(x, 16) for x in res]

    def eth_calls(self, to, datas, block):
        res = self.map([("eth_call", [{"to": to, "data": d}, hex(block)]) for d in datas])
        return res


# ABI helpers. Only plain address arguments are needed by this report.

def keccak(data: bytes) -> bytes:
    from Crypto.Hash import keccak as _k
    return _k.new(digest_bits=256, data=data).digest()


def sel(signature):
    return "0x" + keccak(signature.encode()).hex()[:8]


def call_data(signature, *addresses):
    return sel(signature) + "".join(a.lower()[2:].rjust(64, "0") for a in addresses)


def words(hexdata):
    h = hexdata[2:]
    return [int(h[i:i + 64], 16) for i in range(0, len(h), 64)]
