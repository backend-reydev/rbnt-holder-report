"""The measures behind the report, as plain functions over integers (wei).

Nothing here touches the network or the cache, so tests/test_measures.py can
check each one on small hand-made examples.
"""

from itertools import accumulate

ONE_RBNT = 10 ** 18


def band_of(amount_wei, floors_rbnt):
    """Index of the size band an amount falls in; -1 if below the first floor."""
    index = -1
    for k, floor in enumerate(floors_rbnt):
        if amount_wei >= floor * ONE_RBNT:
            index = k
    return index


def short_size(rbnt):
    """1,000 / 10 million / 1 billion, for band names."""
    if rbnt >= 10 ** 9:
        return f"{rbnt // 10 ** 9:,} billion"
    if rbnt >= 10 ** 6:
        return f"{rbnt // 10 ** 6:,} million"
    return f"{rbnt:,}"


def band_name(floor, ceiling):
    if ceiling is None:
        return f"{short_size(floor)} or more"
    if floor == 0:
        return f"Under {short_size(ceiling)}"
    return f"{short_size(floor)} up to {short_size(ceiling)}"


def share_of_top(amounts, how_many):
    """Fraction of the total held by the `how_many` largest amounts."""
    whole = sum(amounts)
    return sum(sorted(amounts)[-how_many:]) / whole if whole and how_many else 0.0


def holders_for_majority(amounts):
    """How many of the largest holders it takes to hold more than half."""
    whole = sum(amounts)
    for count, running in enumerate(accumulate(sorted(amounts, reverse=True)), 1):
        if 2 * running > whole:
            return count
    return len(amounts)


def gini_index(amounts):
    """0 when everyone holds the same, approaching 1 when one holder has it all."""
    ordered = sorted(amounts)
    n, whole = len(ordered), sum(ordered)
    if not n or not whole:
        return 0.0
    rank_weighted = sum(rank * value for rank, value in enumerate(ordered, 1))
    return (2 * rank_weighted - (n + 1) * whole) / (n * whole)


def lorenz_points(amounts, steps=100):
    """[(share of holders, share held)], smallest holders first, from (0, 0) to (1, 1)."""
    ordered = sorted(amounts)
    n, whole = len(ordered), sum(ordered)
    cumulative = [0] + list(accumulate(ordered))
    return [(k / steps, cumulative[round(n * k / steps)] / whole if whole else 0.0) for k in range(steps + 1)]


def outcome(before, after, band=0.01, floor=ONE_RBNT):
    """What happened to a holding over the quarter: up, flat, down or emptied."""
    if after < floor:
        return "emptied"
    if after * 100 > before * 100 * (1 + band):
        return "up"
    if after * 100 < before * 100 * (1 - band):
        return "down"
    return "flat"


def fold_small_bands(bands, size_key, smallest=5):
    """Merge any band with fewer than `smallest` members into the band below it.

    `bands` run from smallest to largest; each is a dict with numeric fields plus
    `floor` and `ceiling`. The first band is never folded away.
    """
    out = [dict(b) for b in bands]
    k = len(out) - 1
    while k > 0:
        if out[k][size_key] < smallest:
            below = out[k - 1]
            for field, value in out[k].items():
                if field not in ("floor", "ceiling") and isinstance(value, (int, float)):
                    below[field] = below.get(field, 0) + value
            below["ceiling"] = out[k]["ceiling"]
            del out[k]
        k -= 1
    return out


def change_pct(after, before):
    return (after - before) / before * 100 if before else 0.0
