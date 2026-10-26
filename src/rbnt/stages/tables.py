"""Turn the cache into the published tables and headline.json.

Nothing is written until every exact check below holds to the wei. No table
written here carries an unnamed address: unnamed addresses are only ever
counted inside groups of at least five.
"""

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone

from .. import edition, ledger
from .. import measures as M
from ..abi import topic
from ..node import Node

WEI = 10 ** 18
PASSED = []

RESERVED = "Redbelly reserved wallets"
UNNAMED = "Unnamed wallets"
REWARDS = "Reward reserve in the Reddex pools"
EXCESS = "Excess RBNT in the WRBNT contract"
UNREACHED = "Not reached by the scan"
LEFTOVER = "Remaining contracts"


def must(statement, holds, detail=""):
    """Record an exact check, and stop everything if it does not hold."""
    if not holds:
        raise SystemExit(f"Check did not hold: {statement} ({detail})")
    PASSED.append({"check": statement, "held": True, "detail": str(detail)})


def rbnt(wei):
    return wei / WEI


def save_csv(name, header, rows):
    with open(edition.out_dir() / name, "w", newline="") as fh:
        out = csv.writer(fh)
        out.writerow(header)
        for row in rows:
            out.writerow([f"{x:.6f}" if isinstance(x, float) else x for x in row])
    return name


def run(flags):
    cfg = edition.read()
    con = ledger.open_cache()
    node = Node(cfg["chain"]["rpc_url"])
    supply = cfg["total_supply_rbnt"] * WEI
    five = cfg["min_group_size"]
    floors = cfg["holder_bands"]["edges"]
    snaps = [(label, title, ledger.block_of(con, label)) for label, title in cfg["main_snapshots"]]
    first, last = snaps[0][2], snaps[-1][2]
    heights = [h for _, _, h in snaps]
    wrbnt = cfg["wrbnt"]["address"].lower()
    pools = {p["address"].lower(): p["label"] for p in cfg["staking_pools"]}
    short_pool = {a: ("Reddex no lock pool" if "no lock" in n else "Reddex 365 day pool") for a, n in pools.items()}
    reserved = {w["address"].lower(): w["label"] for w in cfg["reserved_wallets"]["wallets"]}
    tags = dict(con.execute("SELECT addr, name FROM tags"))
    exchange_rx = re.compile(r"exchange|binance|bybit|okx|kucoin|gate\.io|mexc|bitget|htx|coinbase|kraken|crypto\.com"
                             r"|bitmart|lbank|bitfinex|bitstamp|upbit", re.I)
    exchanges = {a: n for a, n in tags.items() if exchange_rx.search(n)}
    named = edition.public_names(cfg)
    for a, n in tags.items():
        named.setdefault(a, n)
    head = {"edition": cfg["edition"], "read_on": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "moments": {label: {"title": title, "block": h} for label, title, h in snaps}}
    written = []

    # Load what the holdings stage read.
    marks = ",".join("?" * len(heights))
    native = {h: {} for h in heights}
    for a, h, w in con.execute(f"SELECT addr, block, wei FROM native_at WHERE block IN ({marks})", heights):
        native[h][a] = int(w)
    tokens = {h: defaultdict(dict) for h in heights}
    for a, h, kind, w in con.execute(f"SELECT addr, block, kind, wei FROM token_at WHERE block IN ({marks})", heights):
        tokens[h][kind][a] = int(w)
    fact = {k: int(v) for k, v in con.execute("SELECT k, v FROM facts WHERE k LIKE '%@%'")}
    bytecode = dict(con.execute("SELECT addr, kind FROM bytecode_kind"))
    program = dict(con.execute("SELECT addr, name FROM program_name"))
    # Month ends were only read for addresses that could have changed; the rest hold what they held at both ends.
    for _, _, h in snaps[1:3]:
        for a, w in native[first].items():
            if a not in native[h] and native[last].get(a) == w:
                native[h][a] = w

    # 1. Supply, WRBNT backing and pool totals.
    rows = []
    for label, title, h in snaps:
        found = sum(native[h].values())
        w_supply, w_backing = fact[f"wrbnt_supply@{h}"], fact[f"wrbnt_balance@{h}"]
        w_sum = sum(tokens[h]["wrbnt"].values())
        must(f"{title}: the WRBNT supply equals the sum of every WRBNT balance", w_supply == w_sum, f"{w_supply} {w_sum}")
        must(f"{title}: the WRBNT contract holds at least as much RBNT as the WRBNT supply", w_backing >= w_supply)
        row = [title, h, rbnt(found), rbnt(supply - found), f"{found / supply * 100:.5f}", rbnt(w_supply),
               rbnt(w_backing), rbnt(w_backing - w_supply)]
        for p in pools:
            staked, held = fact[f"total_stake:{p}@{h}"], fact[f"pool_balance:{p}@{h}"]
            stakers_sum = sum(tokens[h][f"stake:{p}"].values())
            must(f"{title}: stakes in the {short_pool[p]} add up to its totalStake", staked == stakers_sum,
                 f"{staked} {stakers_sum}")
            must(f"{title}: the {short_pool[p]} holds at least its totalStake", held >= staked)
            row += [rbnt(held), rbnt(staked), rbnt(held - staked)]
        must(f"{title}: balances found cover more than 99.99% of supply", found * 10000 > supply * 9999,
             f"{found / supply:.6%}")
        must(f"{title}: balances found do not exceed supply", found <= supply)
        rows.append(row)
    header = ["moment", "block", "rbnt_found", "rbnt_not_reached", "pct_of_supply_found", "wrbnt_supply",
              "wrbnt_contract_rbnt", "wrbnt_contract_excess"]
    for p in pools:
        tag = "no_lock" if "no lock" in pools[p] else "lock_365"
        header += [f"{tag}_rbnt", f"{tag}_total_stake", f"{tag}_reward_reserve"]
    written.append(save_csv("supply_reconciliation.csv", header, rows))
    head["supply"] = {"total": cfg["total_supply_rbnt"], "found_pct_end": float(rows[-1][4]),
                      "not_reached_end": rows[-1][3], "not_reached_start": rows[0][3]}

    # 2. Holdings: RBNT + WRBNT + staked, counted with the owner.
    rules = [(re.compile(rx), name) for rx, name in cfg["contract_kinds"]["rules"]]

    def program_kind(a):
        n = (program.get(a) or "").lower().split("->")[-1].strip()
        return next(name for rx, name in rules if rx.search(n))

    def raw_group(a):
        if a in reserved:
            return RESERVED
        if a in pools:
            return REWARDS
        if a == wrbnt:
            return EXCESS
        if a in exchanges:
            return "Labelled exchange wallets"
        if a in tags:
            return "Other explorer-tagged addresses"
        if bytecode.get(a) == "contract":
            return program_kind(a)
        return UNNAMED

    def holdings(h):
        total, parts = defaultdict(int), {"in_wallet": defaultdict(int), "wrapped": defaultdict(int),
                                          "staked": defaultdict(int)}
        for a, w in native[h].items():
            if a != wrbnt and a not in pools:
                total[a] += w
                parts["in_wallet"][a] += w
        for a, w in tokens[h]["wrbnt"].items():
            total[a] += w
            parts["wrapped"][a] += w
        for p in pools:
            for a, w in tokens[h][f"stake:{p}"].items():
                total[a] += w
                parts["staked"][a] += w
            total[p] += fact[f"pool_balance:{p}@{h}"] - fact[f"total_stake:{p}@{h}"]
        total[wrbnt] += fact[f"wrbnt_balance@{h}"] - fact[f"wrbnt_supply@{h}"]
        return total, parts

    HOLD, PARTS = {}, {}
    for label, title, h in snaps:
        HOLD[h], PARTS[h] = holdings(h)
        must(f"{title}: holdings add up to the RBNT found", sum(HOLD[h].values()) == sum(native[h].values()))

    members = defaultdict(set)
    for h in heights:
        for a, w in HOLD[h].items():
            if w >= WEI and bytecode.get(a) == "contract" and a not in named:
                members[program_kind(a)].add(a)
    folded = {k for k, m in members.items() if len(m) < five} | {LEFTOVER}

    def group(a):
        g = raw_group(a)
        return LEFTOVER if g in folded else g

    in_group = defaultdict(set)
    for h in heights:
        for a, w in HOLD[h].items():
            if w >= WEI:
                in_group[group(a)].add(a)

    # 3. Where the coins physically sit.
    places = []
    for label, title, h in snaps:
        at = defaultdict(int)
        for a, w in native[h].items():
            if a in reserved:
                at["Reserved wallets"] += w
            elif a == wrbnt:
                at["WRBNT contract (backing for WRBNT)"] += w
            elif a in pools:
                at[short_pool[a]] += w
            elif bytecode.get(a) == "contract":
                at["All other contracts"] += w
            else:
                at["All other wallets"] += w
        at[UNREACHED] = supply - sum(native[h].values())
        places.append((title, at))
    order = ["Reserved wallets", "WRBNT contract (backing for WRBNT)", "Reddex no lock pool", "Reddex 365 day pool",
             "All other contracts", "All other wallets", UNREACHED]
    written.append(save_csv("location_by_place.csv", ["place"] + [t for t, _ in places] + ["change", "share_at_end_pct"],
                            [[k] + [rbnt(at[k]) for _, at in places] + [rbnt(places[-1][1][k] - places[0][1][k]),
                                                                        places[-1][1][k] / supply * 100] for k in order]))
    head["places"] = {k: {"start": rbnt(places[0][1][k]), "end": rbnt(places[-1][1][k])} for k in order}

    by_group = []
    for label, title, h in snaps:
        sums = defaultdict(int)
        for a, w in HOLD[h].items():
            sums[group(a)] += w
        sums[UNREACHED] = supply - sum(native[h].values())
        by_group.append((title, sums))
    names_sorted = sorted({k for _, s in by_group for k in s if k != UNREACHED}, key=lambda k: -by_group[-1][1].get(k, 0))
    rows = []
    for k in names_sorted + [UNREACHED]:
        size = len(in_group[k]) if k != UNREACHED else ""
        if k not in (UNNAMED, RESERVED, UNREACHED, REWARDS, EXCESS):
            must(f"The group '{k}' has at least {five} members", size >= five, size)
        s, e = by_group[0][1].get(k, 0), by_group[-1][1].get(k, 0)
        rows.append([k, size] + [rbnt(sums.get(k, 0)) for _, sums in by_group] + [rbnt(e - s), e / supply * 100])
    must("Changes across all groups net to the change in RBNT found",
         sum(by_group[-1][1].values()) == sum(by_group[0][1].values()))
    written.append(save_csv("holdings_by_group.csv", ["group", "addresses_with_1_rbnt_or_more_in_quarter"] +
                            [t for t, _ in by_group] + ["change", "share_at_end_pct"], rows))
    head["groups"] = {r[0]: {"members": r[1], "start": r[2], "end": r[5], "change": r[6], "share_end_pct": r[7]}
                      for r in rows}

    # 4. Unnamed wallets: size bands and concentration.
    WALLETS = {h: {a: w for a, w in HOLD[h].items() if group(a) == UNNAMED} for h in heights}
    bands = []
    for k, floor in enumerate(floors):
        ceiling = floors[k + 1] if k + 1 < len(floors) else None
        b = {"floor": floor, "ceiling": ceiling}
        for _, title, h in snaps:
            picked = [w for w in WALLETS[h].values() if M.band_of(w, floors) == k]
            b[f"n:{title}"], b[f"rbnt:{title}"] = len(picked), sum(picked)
        bands.append(b)
    while True:
        thin = [k for k in range(1, len(bands)) if min(bands[k][f"n:{t}"] for _, t, _ in snaps) < five]
        if not thin:
            break
        k = thin[-1]
        for f, v in bands[k].items():
            if f.startswith(("n:", "rbnt:")):
                bands[k - 1][f] += v
        bands[k - 1]["ceiling"] = bands[k]["ceiling"]
        del bands[k]
    rows = [[M.band_name(b["floor"], b["ceiling"])] + [b[f"n:{t}"] for _, t, _ in snaps] +
            [rbnt(b[f"rbnt:{t}"]) for _, t, _ in snaps] for b in bands]
    written.append(save_csv("size_bands.csv", ["holding_rbnt"] + [f"wallets {t}" for _, t, _ in snaps] +
                            [f"rbnt {t}" for _, t, _ in snaps], rows))
    head["bands"] = [{"band": r[0], "wallets_start": r[1], "wallets_end": r[4], "rbnt_start": r[5], "rbnt_end": r[8]}
                     for r in rows]
    head["dust_wallets"] = {t: sum(1 for w in WALLETS[h].values() if 0 < w < WEI) for _, t, h in snaps}

    rows = []
    for _, title, h in snaps:
        vals = [w for w in WALLETS[h].values() if w >= WEI]
        mid = sorted(vals)[len(vals) // 2]
        rows.append([title, h, len(vals), rbnt(sum(vals)), M.share_of_top(vals, 10) * 100, M.share_of_top(vals, 100) * 100,
                     M.share_of_top(vals, 1000) * 100, M.share_of_top(vals, max(1, len(vals) // 100)) * 100,
                     M.holders_for_majority(vals), M.gini_index(vals), rbnt(mid)])
    written.append(save_csv("concentration_measures.csv",
                            ["moment", "block", "wallets_with_1_rbnt_or_more", "rbnt_they_hold", "top_10_pct",
                             "top_100_pct", "top_1000_pct", "top_1_percent_of_wallets_pct", "wallets_holding_half",
                             "gini", "median_rbnt"], rows))
    head["concentration"] = {r[0]: {"wallets": r[2], "rbnt": r[3], "top10": r[4], "top100": r[5], "top1000": r[6],
                                    "top1pct": r[7], "to_half": r[8], "gini": r[9], "median": r[10]} for r in rows}
    p0 = M.lorenz_points([w for w in WALLETS[first].values() if w >= WEI], 200)
    p1 = M.lorenz_points([w for w in WALLETS[last].values() if w >= WEI], 200)
    written.append(save_csv("lorenz_points.csv", ["share_of_wallets", "share_of_rbnt_pct_start", "share_of_rbnt_pct_end"],
                            [[f"{x:.3f}", f"{a * 100:.4f}", f"{b * 100:.4f}"] for (x, a), (_, b) in zip(p0, p1)]))

    # 5. The same wallets followed from start to end.
    w0, w1 = WALLETS[first], WALLETS[last]
    band_width = cfg["change_threshold"]
    cohort_rows = []
    for b in bands:
        lo, hi = b["floor"] * WEI, (b["ceiling"] * WEI if b["ceiling"] else None)
        group_ = [a for a, w in w0.items() if w >= lo and (hi is None or w < hi)]
        tally = defaultdict(int)
        for a in group_:
            tally[M.outcome(w0[a], w1.get(a, 0), band_width)] += 1
        s, e = sum(w0[a] for a in group_), sum(w1.get(a, 0) for a in group_)
        cohort_rows.append([M.band_name(b["floor"], b["ceiling"]), len(group_), rbnt(s), rbnt(e), rbnt(e - s),
                            tally["up"], tally["flat"], tally["down"], tally["emptied"]])
    arrivals = [a for a, w in w1.items() if w >= WEI and w0.get(a, 0) < WEI]
    cohort_rows.append(["Under 1 on 30 June", len(arrivals), rbnt(sum(w0.get(a, 0) for a in arrivals)),
                        rbnt(sum(w1[a] for a in arrivals)), rbnt(sum(w1[a] - w0.get(a, 0) for a in arrivals)),
                        "", "", "", ""])
    written.append(save_csv("cohort_outcomes.csv", ["holding_on_30_june", "wallets", "rbnt_start", "rbnt_end", "net",
                                                    "up_more_than_1pct", "flat_within_1pct", "down_more_than_1pct",
                                                    "fell_below_1_rbnt"], cohort_rows))
    head["cohorts"] = [dict(zip(["cohort", "wallets", "start", "end", "net", "up", "flat", "down", "emptied"], r))
                       for r in cohort_rows]

    labels = ["Under 1"] + [M.band_name(b["floor"], b["ceiling"]) for b in bands]

    def slot(w):
        if w < WEI:
            return 0
        return 1 + next(k for k, b in enumerate(bands)
                        if w >= b["floor"] * WEI and (b["ceiling"] is None or w < b["ceiling"] * WEI))
    grid = [[0] * len(labels) for _ in labels]
    for a in set(w0) | set(w1):
        s, e = w0.get(a, 0), w1.get(a, 0)
        if s >= WEI or e >= WEI:
            grid[slot(s)][slot(e)] += 1
    shown = [[labels[r]] + [c if c == 0 or c >= five else f"<{five}" for c in grid[r]] for r in range(len(labels))]
    written.append(save_csv("band_transitions.csv", ["from_band_on_30_june / to_band_on_30_september"] + labels, shown))
    head["transitions"] = {"labels": labels, "grid": shown}

    ranked = sorted(w0.items(), key=lambda kv: -kv[1])
    rank_rows = []
    for lo, hi, title in cfg["top_groups"]:
        members_ = [(a, w) for a, w in (ranked[lo - 1:hi] if hi else ranked[lo - 1:]) if w >= WEI]
        tally = defaultdict(int)
        mix = {k: [0, 0] for k in ("in_wallet", "wrapped", "staked")}
        for a, w in members_:
            tally[M.outcome(w, w1.get(a, 0), band_width)] += 1
            for k in mix:
                mix[k][0] += PARTS[first][k].get(a, 0)
                mix[k][1] += PARTS[last][k].get(a, 0)
        s, e = sum(w for _, w in members_), sum(w1.get(a, 0) for a, _ in members_)
        rank_rows.append([title, len(members_), rbnt(s), rbnt(e), rbnt(e - s), M.change_pct(e, s), tally["up"],
                          tally["flat"], tally["down"], tally["emptied"]] + [rbnt(mix[k][i]) for k in mix for i in (0, 1)])
    written.append(save_csv("rank_groups.csv",
                            ["group_ranked_on_30_june", "wallets", "rbnt_start", "rbnt_end", "net", "change_pct",
                             "up_more_than_1pct", "flat_within_1pct", "down_more_than_1pct", "fell_below_1_rbnt",
                             "in_wallet_start", "in_wallet_end", "wrapped_start", "wrapped_end", "staked_start",
                             "staked_end"], rank_rows))
    head["ranks"] = [dict(zip(["group", "wallets", "start", "end", "net", "pct", "up", "flat", "down", "emptied",
                               "in_wallet_start", "in_wallet_end", "wrapped_start", "wrapped_end", "staked_start",
                               "staked_end"], r)) for r in rank_rows]

    # 6. Staking.
    days = ledger.moments(con, "day")
    written.append(save_csv("pools_daily.csv", ["day_starting_utc", "block"] +
                            [f"{'no_lock' if 'no lock' in pools[p] else 'lock_365'}_{x}" for p in pools
                             for x in ("rbnt", "total_stake")] + ["wrbnt_supply"],
                            [[label[4:], h] + [rbnt(fact[f"{k}:{p}@{h}"]) for p in pools
                                               for k in ("pool_balance", "total_stake")] +
                             [rbnt(fact[f"wrbnt_supply@{h}"])] for label, h, _ in days]))
    events = defaultdict(list)
    for h, topics_json, data, addr in con.execute(
            "SELECT block, topics, data, address FROM watched_logs WHERE block > ? AND block <= ?", (first, last)):
        events[addr].append((json.loads(topics_json)[0], data))
    T_STAKE = topic("Stake(address,uint256,uint256,uint256)")
    T_UNSTAKE = topic("Unstake(address,uint256,uint256,uint256)")
    T_CLAIM = topic("ClaimLiquidXReward(address,uint256)")
    STAKE_FN = "0x3a4b66f1"       # stake()
    pool_rows = []
    head["pools"] = {}
    for p in pools:
        count = defaultdict(lambda: [0, 0])
        for t0, data in events[p]:
            for name, t in (("stake", T_STAKE), ("unstake", T_UNSTAKE), ("claim", T_CLAIM)):
                if t0 == t:
                    count[name][0] += 1
                    count[name][1] += int(data[66:130], 16)
        top_ups = sum(int(v) for (v,) in con.execute(
            "SELECT value FROM quarter_tx WHERE recipient = ? AND status = 1 AND input4 != ? AND value != '0'",
            (p, STAKE_FN)))
        top_ups += sum(int(v) for (v,) in con.execute(
            "SELECT value FROM inner_transfers WHERE recipient = ? AND is_error = 0 AND type = 'call'", (p,)))
        k = f"stake:{p}"
        before = {a for a, w in tokens[first][k].items() if w}
        after = {a for a, w in tokens[last][k].items() if w}
        b0, b1 = fact[f"pool_balance:{p}@{first}"], fact[f"pool_balance:{p}@{last}"]
        s0, s1 = fact[f"total_stake:{p}@{first}"], fact[f"total_stake:{p}@{last}"]
        must(f"{short_pool[p]}: RBNT in Stake records minus Unstake records equals the change in totalStake",
             count["stake"][1] - count["unstake"][1] == s1 - s0)
        row = [short_pool[p], rbnt(b0), rbnt(b1), rbnt(b1 - b0), M.change_pct(b1, b0), rbnt(s0), rbnt(s1), rbnt(s1 - s0),
               rbnt(b0 - s0), rbnt(b1 - s1), len(before), len(after), len(after - before), len(before - after),
               count["stake"][0], rbnt(count["stake"][1]), count["unstake"][0], rbnt(count["unstake"][1]),
               count["claim"][0], rbnt(count["claim"][1]), rbnt(top_ups)]
        pool_rows.append(row)
        head["pools"][short_pool[p]] = dict(zip(
            ["rbnt_start", "rbnt_end", "rbnt_change", "rbnt_change_pct", "staked_start", "staked_end", "staked_change",
             "reserve_start", "reserve_end", "stakers_start", "stakers_end", "joined", "left", "stakes", "staked_in",
             "withdrawals", "withdrawn", "claims", "claimed", "top_ups"], row[1:]))
    written.append(save_csv("pools_summary.csv",
                            ["pool", "rbnt_start", "rbnt_end", "rbnt_change", "rbnt_change_pct", "total_stake_start",
                             "total_stake_end", "total_stake_change", "reward_reserve_start", "reward_reserve_end",
                             "stakers_start", "stakers_end", "stakers_joined", "stakers_left", "stake_records",
                             "rbnt_staked", "unstake_records", "rbnt_unstaked", "reward_claims", "rbnt_rewards_paid",
                             "plain_transfers_in"], pool_rows))
    both0, both1 = sum(r[1] for r in pool_rows), sum(r[2] for r in pool_rows)
    head["pools"]["both"] = {"rbnt_start": both0, "rbnt_end": both1, "change_pct": M.change_pct(both1, both0),
                             "staked_start": sum(r[5] for r in pool_rows), "staked_end": sum(r[6] for r in pool_rows)}
    for (_, _, h), key in ((snaps[0], "start"), (snaps[-1], "end")):
        held = sum(WALLETS[h].values())
        staked = sum(PARTS[h]["staked"].get(a, 0) for a in WALLETS[h])
        head["pools"]["both"][f"wallet_share_staked_{key}"] = staked / held * 100

    rows = []
    for p in pools:
        sizes = [w for w in tokens[last][f"stake:{p}"].values() if w]
        bucket = []
        for k, floor in enumerate([0] + floors[1:]):
            ceiling = floors[k + 1] if k + 1 < len(floors) else None
            picked = [w for w in sizes if w >= floor * WEI and (ceiling is None or w < ceiling * WEI)]
            bucket.append({"floor": floor, "ceiling": ceiling, "n": len(picked), "amount": sum(picked)})
        for b in M.fold_small_bands(bucket, "n", five):
            rows.append([short_pool[p], M.band_name(b["floor"], b["ceiling"]), b["n"], rbnt(b["amount"])])
    written.append(save_csv("stake_size_bands.csv", ["pool", "stake_rbnt", "stakers", "rbnt_staked"], rows))

    month_ends = int(datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp())
    schedule = defaultdict(lambda: [0, 0])
    lock_pool = next(p for p in pools if "365" in pools[p])
    for amount, when in con.execute("SELECT amount, unlock_ts FROM locks WHERE pool = ?", (lock_pool,)):
        month = "Already past its lock" if when <= month_ends else datetime.fromtimestamp(when, timezone.utc).strftime("%Y-%m")
        schedule[month][0] += 1
        schedule[month][1] += int(amount)
    must("The unlock schedule of the 365 day pool adds up to its totalStake",
         sum(v[1] for v in schedule.values()) == fact[f"total_stake:{lock_pool}@{last}"])
    rows = [[m, n if n >= five else f"<{five}", rbnt(a)]
            for m, (n, a) in sorted(schedule.items(), key=lambda kv: (kv[0][0] != "A", kv[0]))]
    written.append(save_csv("unlock_schedule_365.csv", ["unlock_month_utc", "open_stakes", "rbnt"], rows))
    head["unlocks"] = rows

    # 7. Named wallets: balances, counterparties, exact reconciliation.
    kinds_seen = {}

    def kind_now(a):
        if a in bytecode:
            return "contract" if bytecode[a] == "contract" else "wallet"
        if a not in kinds_seen:
            code = node.one("eth_getCode", a, hex(last))
            kinds_seen[a] = "contract" if code not in ("0x", "0x0") and not code.startswith("0xef0100") else "wallet"
        return kinds_seen[a]

    def party(a):
        if a in reserved:
            return reserved[a]
        if a in pools:
            return short_pool[a]
        if a == wrbnt:
            return "WRBNT contract"
        if a in exchanges:
            return "Labelled exchange wallets"
        if a in tags:
            return tags[a]
        if kind_now(a) == "contract":
            return group(a) if a in program else "Contracts with no published code"
        return UNNAMED

    named_rows, party_rows = [], []
    listing = [(a, reserved[a], "Reserved wallet") for a in reserved] + [(wrbnt, cfg["wrbnt"]["label"], "Wrapped RBNT")] \
        + [(p, pools[p], "Staking pool") for p in pools]
    for a, title, category in listing:
        s, e = native[first][a], native[last][a]
        flow = defaultdict(lambda: [0, 0, 0, 0])
        fees = 0
        moves = list(con.execute("SELECT sender, recipient, value, fee, status FROM quarter_tx "
                                 "WHERE sender = ? OR recipient = ?", (a, a)))
        for snd, rcp, val, fee, ok in moves:
            if snd == a:
                fees += int(fee)
        moves = [(snd, rcp, val) for snd, rcp, val, fee, ok in moves if ok == 1]
        moves += list(con.execute("SELECT sender, recipient, value FROM inner_transfers WHERE (sender = ? OR recipient = ?) "
                                  "AND is_error = 0 AND type IN ('call', 'create', 'create2')", (a, a)))
        for snd, rcp, val in moves:
            if val == "0" or snd == rcp:
                continue
            if rcp == a:
                f = flow[party(snd)]
                f[0] += int(val)
                f[1] += 1
            else:
                f = flow[party(rcp)]
                f[2] += int(val)
                f[3] += 1
        got, sent = sum(f[0] for f in flow.values()), sum(f[2] for f in flow.values())
        gap = e - (s + got - sent - fees)
        must(f"{title}: start + RBNT in - RBNT out - fees = end", gap == 0, f"gap {gap} wei")
        named_rows.append([category, title, a, rbnt(s), rbnt(e), rbnt(e - s), rbnt(got), rbnt(sent), rbnt(fees), gap])
        for who, (ia, ic, oa, oc) in sorted(flow.items(), key=lambda kv: -(kv[1][0] + kv[1][2])):
            party_rows.append([title, who, rbnt(ia), ic, rbnt(oa), oc])
    written.append(save_csv("named_balances.csv", ["category", "name", "address", "rbnt_start", "rbnt_end", "change",
                                                   "rbnt_in", "rbnt_out", "fees", "gap_wei"], named_rows))
    written.append(save_csv("named_counterparties.csv", ["named_wallet", "counterparty", "rbnt_in", "transfers_in",
                                                         "rbnt_out", "transfers_out"], party_rows))
    head["named"] = {r[1]: {"start": r[3], "end": r[4], "change": r[5], "in": r[6], "out": r[7], "fees": r[8]}
                     for r in named_rows}
    head["counterparties"] = [dict(zip(["wallet", "party", "in", "in_n", "out", "out_n"], r)) for r in party_rows]
    head["exchange_tags"] = list(exchanges.values())
    head["all_tags"] = list(tags.values())

    T_TRANSFER = topic("Transfer(address,address,uint256)")
    T_DEPOSIT, T_WITHDRAW = topic("Deposit(address,uint256)"), topic("Withdrawal(address,uint256)")
    wrapped = defaultdict(lambda: [0, 0])
    token_flow = defaultdict(lambda: [0, 0])

    def flow_group(a):
        if a in reserved:
            return RESERVED
        if a in pools:
            return "Reddex staking pools"
        if a == wrbnt:
            return "WRBNT contract"
        if kind_now(a) == "contract":
            return group(a) if a in program else "Contracts with no published code"
        return UNNAMED

    for h, topics_json, data in con.execute("SELECT block, topics, data FROM watched_logs WHERE address = ? "
                                            "AND block > ? AND block <= ?", (wrbnt, first, last)):
        t = json.loads(topics_json)
        if t[0] == T_TRANSFER:
            src, dst, amount = "0x" + t[1][-40:], "0x" + t[2][-40:], int(data, 16)
            token_flow[(flow_group(src), flow_group(dst))][0] += amount
            token_flow[(flow_group(src), flow_group(dst))][1] += 1
            for me, verb, other in ((src, "sent", dst), (dst, "received", src)):
                if me in reserved:
                    wrapped[(reserved[me], f"WRBNT {verb}", party(other))][0] += amount
                    wrapped[(reserved[me], f"WRBNT {verb}", party(other))][1] += 1
        elif t[0] in (T_DEPOSIT, T_WITHDRAW) and "0x" + t[1][-40:] in reserved:
            key = (reserved["0x" + t[1][-40:]], "Wrapped RBNT" if t[0] == T_DEPOSIT else "Unwrapped WRBNT", "")
            wrapped[key][0] += int(data, 16)
            wrapped[key][1] += 1
    written.append(save_csv("reserved_wrbnt.csv", ["reserved_wallet", "movement", "counterparty", "wrbnt", "transfers"],
                            [[a, m, c, rbnt(v), n] for (a, m, c), (v, n) in sorted(wrapped.items())]))
    head["reserved_wrbnt"] = [{"wallet": a, "movement": m, "party": c, "amount": rbnt(v), "n": n}
                              for (a, m, c), (v, n) in sorted(wrapped.items())]

    coin_flow = defaultdict(lambda: [0, 0])
    for snd, rcp, val in con.execute("SELECT sender, recipient, value FROM quarter_tx WHERE status = 1 AND value != '0'"):
        if rcp:
            coin_flow[(flow_group(snd), flow_group(rcp))][0] += int(val)
            coin_flow[(flow_group(snd), flow_group(rcp))][1] += 1
    for snd, rcp, val in con.execute("SELECT sender, recipient, value FROM inner_transfers WHERE is_error = 0 "
                                     "AND type IN ('call', 'create', 'create2') AND value != '0'"):
        if rcp:
            coin_flow[(flow_group(snd), flow_group(rcp))][0] += int(val)
            coin_flow[(flow_group(snd), flow_group(rcp))][1] += 1
    pairs = sorted(set(coin_flow) | set(token_flow), key=lambda k: -(coin_flow[k][0] + token_flow[k][0]))
    written.append(save_csv("group_flows.csv", ["from_group", "to_group", "rbnt", "rbnt_transfers", "wrbnt",
                                                "wrbnt_transfers", "together"],
                            [[f, t, rbnt(coin_flow[(f, t)][0]), coin_flow[(f, t)][1], rbnt(token_flow[(f, t)][0]),
                              token_flow[(f, t)][1], rbnt(coin_flow[(f, t)][0] + token_flow[(f, t)][0])]
                             for f, t in pairs]))
    head["group_flows"] = [{"from": f, "to": t, "rbnt": rbnt(coin_flow[(f, t)][0]), "wrbnt": rbnt(token_flow[(f, t)][0]),
                            "together": rbnt(coin_flow[(f, t)][0] + token_flow[(f, t)][0]),
                            "transfers": coin_flow[(f, t)][1] + token_flow[(f, t)][1]} for f, t in pairs]

    reserved_list = list(reserved)
    daily = {(a, h): int(w) for a, h, w in con.execute(
        f"SELECT addr, block, wei FROM native_at WHERE addr IN ({','.join('?' * len(reserved_list))})", reserved_list)}
    written.append(save_csv("reserved_daily.csv", ["day_starting_utc", "block"] + [reserved[a] for a in reserved_list],
                            [[label[4:], h] + [rbnt(daily[(a, h)]) for a in reserved_list] for label, h, _ in days]))

    head["chain_work"] = {
        "blocks_read": last + 1,
        "addresses_found": con.execute("SELECT count(*) FROM seen").fetchone()[0],
        "inner_transfer_rows": int(ledger.recall(con, "inner_rows", 0)),
        "explorer_rows_read": int(ledger.recall(con, "explorer_rows_read", 0)),
        "quarter_transactions": con.execute("SELECT count(*) FROM quarter_tx").fetchone()[0],
        "quarter_fees_rbnt": rbnt(sum(int(f) for (f,) in con.execute("SELECT fees FROM quarter_block"))),
    }
    head["checks"] = PASSED
    head["tables"] = written
    (edition.out_dir() / "headline.json").write_text(json.dumps(head, indent=2, default=str) + "\n")
    print(f"  {len(PASSED)} exact checks held; wrote {len(written)} tables and headline.json")
