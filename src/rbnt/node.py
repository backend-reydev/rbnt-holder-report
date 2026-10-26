"""Talking to the Redbelly mainnet node over JSON-RPC.

The public node takes at most 100 requests per batch and refuses a batch whose
answer is too large. `many()` cuts any list of requests into batches, sends
them from a pool of threads and hands the answers back in the original order.
A refused batch is halved straight away; a failed one is retried with growing
pauses, then halved, so a single bad request can be pinned down.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

BATCH_LIMIT = 100


class NodeError(RuntimeError):
    pass


class AnswerTooLarge(NodeError):
    pass


class Node:
    def __init__(self, url, threads=24):
        self.url = url
        self.threads = threads
        self._tls = threading.local()

    def _http(self):
        if getattr(self._tls, "http", None) is None:
            self._tls.http = requests.Session()
        return self._tls.http

    def one(self, method, *params):
        return self.send([(method, list(params))])[0]

    def send(self, requests_, attempts=6):
        payload = []
        for n, (method, params) in enumerate(requests_):
            payload.append({"jsonrpc": "2.0", "id": n, "method": method, "params": params})
        problem = None
        for attempt in range(attempts):
            try:
                reply = self._http().post(self.url, json=payload, timeout=120)
                reply.raise_for_status()
                answers = reply.json()
                if not isinstance(answers, list):
                    raise NodeError(answers.get("error"))
                by_id = {a["id"]: a for a in answers}
                failures = [a["error"] for a in answers if "error" in a]
                if failures and len(requests_) > 1 and any("too large" in str(f.get("message")) for f in failures):
                    raise AnswerTooLarge(failures[0])
                if failures:
                    raise NodeError(failures[0])
                return [by_id[n]["result"] for n in range(len(requests_))]
            except AnswerTooLarge:
                break
            except (requests.RequestException, NodeError, ValueError, KeyError) as err:
                problem = err
                time.sleep(min(30, 1.5 ** attempt))
        if len(requests_) == 1:
            raise NodeError(f"{requests_[0]} failed: {problem}")
        half = len(requests_) // 2
        return self.send(requests_[:half], attempts) + self.send(requests_[half:], attempts)

    def many(self, requests_, report=None):
        batches = [requests_[k:k + BATCH_LIMIT] for k in range(0, len(requests_), BATCH_LIMIT)]
        answers = []
        with ThreadPoolExecutor(self.threads) as pool:
            for n, part in enumerate(pool.map(self.send, batches), 1):
                answers.extend(part)
                if report and n % 250 == 0:
                    report(n, len(batches))
        return answers

    # Shortcuts used by the stages.

    def block(self, height, with_transactions=False):
        return self.one("eth_getBlockByNumber", hex(height), with_transactions)

    def balances_at(self, addresses, height):
        return [int(v, 16) for v in self.many([("eth_getBalance", [a, hex(height)]) for a in addresses])]

    def calls_at(self, contract, call_datas, height):
        return self.many([("eth_call", [{"to": contract, "data": d}, hex(height)]) for d in call_datas])
