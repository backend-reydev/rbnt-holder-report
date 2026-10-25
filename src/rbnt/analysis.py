"""Pure functions behind the report's measures. All amounts are integers in wei.

Kept free of I/O so they can be unit tested (tests/test_analysis.py).
"""

from bisect import bisect_right

WEI = 10 ** 18


def band_index(wei, edges_rbnt):
    """Index of the band a holding falls in. edges are lower bounds in RBNT."""
    return bisect_right([e * WEI for e in edges_rbnt], wei) - 1


def band_label(i, edges_rbnt):
    lo = edges_rbnt[i]
    hi = edges_rbnt[i + 1] if i + 1 < len(edges_rbnt) else None
    return f"{fmt_rbnt_short(lo)} to {fmt_rbnt_short(hi)}" if hi else f"{fmt_rbnt_short(lo)} and over"


def fmt_rbnt_short(x):
    if x >= 1_000_000_000:
        return f"{x / 1e9:g} billion"
    if x >= 1_000_000:
        return f"{x / 1e6:g} million"
    return f"{x:,}"


def top_share(values, n):
    """Share of the total held by the n largest values."""
    total = sum(values)
    if not total:
        return 0.0
    return sum(sorted(values, reverse=True)[:n]) / total


def count_to_half(values):
    """Smallest number of holders that together hold more than half."""
    total, run = sum(values), 0
    for i, v in enumerate(sorted(values, reverse=True), 1):
        run += v
        if run * 2 > total:
            return i
    return len(values)


def gini(values):
    """Gini coefficient, 0 = everyone holds the same, 1 = one holder has all."""
    xs = sorted(values)
    n, total = len(xs), sum(xs)
    if n == 0 or total == 0:
        return 0.0
    weighted = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * weighted) / (n * total) - (n + 1) / n


def lorenz(values, points=100):
    """(share of holders, share of holdings) pairs, smallest holders first."""
    xs = sorted(values)
    n, total = len(xs), sum(xs)
    out, run, j = [(0.0, 0.0)], 0, 0
    for k in range(1, points + 1):
        upto = round(n * k / points)
        while j < upto:
            run += xs[j]
            j += 1
        out.append((k / points, run / total if total else 0.0))
    return out


def classify_change(start, end, threshold=0.01, floor=WEI):
    """How a holding that started at or above `floor` moved by the end."""
    if end < floor:
        return "exited"
    if end > start * (1 + threshold):
        return "added"
    if end < start * (1 - threshold):
        return "reduced"
    return "steady"


def merge_small(rows, key_count, min_size=5):
    """Fold groups smaller than min_size into the group above them, from the top.

    rows are ordered smallest to largest band. Returns new rows with merged
    labels, so no reported band holds fewer than min_size members.
    """
    out = [dict(r) for r in rows]
    i = len(out) - 1
    while i > 0:
        if out[i][key_count] < min_size:
            lower = out[i - 1]
            for k, v in out[i].items():
                if isinstance(v, (int, float)) and k != "lo":
                    lower[k] = lower.get(k, 0) + v
            lower["hi"] = out[i].get("hi")
            out.pop(i)
        i -= 1
    return out


def pct(a, b):
    return (a - b) / b * 100 if b else 0.0
