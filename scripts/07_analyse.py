"""Step 7. Build every table and headline figure from the cache.

Writes aggregated CSVs and figures.json to data/processed/<edition>/. No file
written here contains an unlabelled address: every unlabelled address is only
counted inside a group of at least min_group_size members.

Runs exact checks in wei before writing anything and stops if any fails.
"""

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone

import _path  # noqa: F401
from rbnt import analysis as A
from rbnt import config, store
from rbnt.rpc import Rpc

WEI = 10 ** 18
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append({"check": name, "passed": bool(ok), "detail": detail})
    if not ok:
        raise SystemExit(f"CHECK FAILED: {name} {detail}")


def rb(wei):
    """wei to RBNT as a float, for output only. All sums are done in wei."""
    return wei / WEI


def write(name, header, rows):
    path = config.data_dir("processed") / name
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([f"{x:.6f}" if isinstance(x, float) else x for x in r])
    return name


def main():
    cfg = config.load()
    db = store.connect()
    rpc = Rpc(cfg["chain"]["rpc_url"])
    supply = cfg["total_supply_rbnt"] * WEI
    min_group = cfg["min_group_size"]
    edges = cfg["holder_bands"]["edges"]
    snaps = [(name, label, store.snapshot(db, name)) for name, label in cfg["main_snapshots"]]
    S0, S1 = snaps[0][2], snaps[-1][2]
    wrbnt = cfg["wrbnt"]["address"].lower()
    pools = {p["address"].lower(): p["label"] for p in cfg["staking_pools"]}
    reserved = {w["address"].lower(): w["label"] for w in cfg["reserved_wallets"]["wallets"]}
    labels = {a: n for a, n in db.execute("SELECT addr, name FROM label")}
    exchange_labels = {a: n for a, n in labels.items()
                       if re.search(r"exchange|binance|bybit|okx|kucoin|gate|mexc|bitget|htx|coinbase|kraken|crypto\.com|bitmart|lbank", n, re.I)}
    named = config.named_wallets(cfg)
    for a, n in labels.items():
        named.setdefault(a, n)
    fig = {"edition": cfg["edition"], "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
           "snapshots": {name: {"label": label, "block": b} for name, label, b in snaps}}
    out_files = []

    # ---- Load balances ------------------------------------------------------
    blocks = [b for _, _, b in snaps]
    native = {b: {} for b in blocks}
    for a, b, wei in db.execute(f"SELECT addr, block, wei FROM balance WHERE block IN ({','.join('?' * 4)})", blocks):
        native[b][a] = int(wei)
    token = {b: defaultdict(dict) for b in blocks}
    for a, b, kind, wei in db.execute(f"SELECT addr, block, kind, wei FROM token WHERE block IN ({','.join('?' * 4)})", blocks):
        token[b][kind][a] = int(wei)
    kv = {k: int(v) for k, v in db.execute("SELECT key, value FROM kv WHERE key LIKE '%@%'")}
    code = {a: k for a, k in db.execute("SELECT addr, kind FROM code")}
    cnames = {a: n for a, n in db.execute("SELECT addr, name FROM contract")}

    # Month-end snapshots only cover addresses that could have changed. Every
    # other address holds the same at a month end as at the start and the end.
    for _, _, b in snaps[1:3]:
        for a, v in native[S0].items():
            if a not in native[b] and native[S1].get(a) == v:
                native[b][a] = v

    # ---- Checks: supply, WRBNT, pools ---------------------------------------
    supply_rows = []
    for name, label, b in snaps:
        read = sum(native[b].values())
        wsup = kv[f"wrbnt_supply@{b}"]
        wbal = kv[f"wrbnt_balance@{b}"]
        wsum = sum(token[b]["wrbnt"].values())
        check(f"WRBNT supply equals the sum of all WRBNT balances at {label}", wsup == wsum, f"{wsup} vs {wsum}")
        check(f"WRBNT contract holds at least the WRBNT supply at {label}", wbal >= wsup, f"{wbal} vs {wsup}")
        row = [label, b, rb(read), rb(supply - read), f"{read / supply * 100:.5f}", rb(wsup), rb(wbal), rb(wbal - wsup)]
        for p in pools:
            ts = kv[f"total_stake:{p}@{b}"]
            ss = sum(token[b][f"stake:{p}"].values())
            pb = kv[f"pool_balance:{p}@{b}"]
            check(f"{pools[p]}: stakers add up to totalStake at {label}", ts == ss, f"{ts} vs {ss}")
            check(f"{pools[p]}: balance covers totalStake at {label}", pb >= ts, f"{pb} vs {ts}")
            row += [rb(pb), rb(ts), rb(pb - ts)]
        check(f"Balances read cover over 99.99% of supply at {label}", read * 10000 > supply * 9999, f"{read / supply:.6%}")
        check(f"Balances read never exceed supply at {label}", read <= supply)
        supply_rows.append(row)
    hdr = ["snapshot", "block", "rbnt_read_from_chain", "rbnt_not_located", "pct_of_supply_located",
           "wrbnt_supply", "wrbnt_contract_rbnt", "wrbnt_contract_surplus"]
    for p in pools:
        short = "no_lock" if "no lock" in pools[p] else "365_day"
        hdr += [f"pool_{short}_balance", f"pool_{short}_total_stake", f"pool_{short}_reward_funds"]
    out_files.append(write("01_supply_check.csv", hdr, supply_rows))
    fig["supply"] = {"total": cfg["total_supply_rbnt"],
                     "located_pct_end": float(supply_rows[-1][4]), "not_located_end": supply_rows[-1][3],
                     "not_located_start": supply_rows[0][3]}

    # ---- Positions -----------------------------------------------------------
    rules = [(re.compile(rx), kind) for rx, kind in cfg["contract_kinds"]["rules"]]

    def contract_kind(a):
        n = (cnames.get(a) or "").lower()
        n = n.split("->")[-1].strip() if "->" in n else n
        return next(kind for rx, kind in rules if rx.search(n))

    def group_of(a):
        if a in reserved:
            return "Redbelly reserved wallets"
        if a in pools:
            return "Reddex pools: reward funds"
        if a == wrbnt:
            return "WRBNT contract surplus"
        if a in exchange_labels:
            return "Labelled exchange wallets"
        if a in labels:
            return "Other explorer-labelled addresses"
        k = code.get(a)
        if k in ("wallet", "delegated"):
            return "Other wallets"
        if k == "contract":
            return contract_kind(a)
        return "Other wallets"

    def positions(b):
        pos = defaultdict(int)
        parts = {"native": defaultdict(int), "wrbnt": defaultdict(int), "staked": defaultdict(int)}
        for a, v in native[b].items():
            if a == wrbnt or a in pools:
                continue
            pos[a] += v
            parts["native"][a] += v
        for a, v in token[b]["wrbnt"].items():
            pos[a] += v
            parts["wrbnt"][a] += v
        for p in pools:
            for a, v in token[b][f"stake:{p}"].items():
                pos[a] += v
                parts["staked"][a] += v
        for p in pools:
            pos[p] += kv[f"pool_balance:{p}@{b}"] - kv[f"total_stake:{p}@{b}"]
        pos[wrbnt] += kv[f"wrbnt_balance@{b}"] - kv[f"wrbnt_supply@{b}"]
        return pos, parts

    POS, PARTS = {}, {}
    for _, _, b in snaps:
        POS[b], PARTS[b] = positions(b)
        total = sum(POS[b].values())
        read = sum(native[b].values())
        check(f"Positions add up to the RBNT read at block {b}", total == read, f"{total} vs {read}")

    # Contract kinds with fewer than min_group contracts fold into Other contracts.
    kind_members = defaultdict(set)
    for b in blocks:
        for a, v in POS[b].items():
            if v >= WEI and code.get(a) == "contract" and a not in named:
                kind_members[contract_kind(a)].add(a)
    small_kinds = {k for k, m in kind_members.items() if len(m) < min_group} | {"Other verified contracts"}

    def final_group(a):
        g = group_of(a)
        return "Other contracts" if g in small_kinds else g

    group_members = defaultdict(set)
    for b in blocks:
        for a, v in POS[b].items():
            if v >= WEI:
                group_members[final_group(a)].add(a)

    # ---- Where RBNT physically sits -------------------------------------------
    rows = []
    for name, label, b in snaps:
        sit = defaultdict(int)
        for a, v in native[b].items():
            if a in reserved:
                sit["Redbelly reserved wallets"] += v
            elif a == wrbnt:
                sit["Wrapped RBNT contract (backs WRBNT)"] += v
            elif a in pools:
                sit[pools[a]] += v
            elif code.get(a) == "contract":
                sit["Other contracts"] += v
            else:
                sit["Other wallets"] += v
        sit["Not located"] = supply - sum(native[b].values())
        rows.append((label, sit))
    order = ["Redbelly reserved wallets", "Wrapped RBNT contract (backs WRBNT)"] + list(pools.values()) + \
            ["Other contracts", "Other wallets", "Not located"]
    out_files.append(write("02_where_rbnt_sits.csv", ["place"] + [l for l, _ in rows] + ["change_rbnt", "share_end_pct"],
                           [[k] + [rb(s[k]) for _, s in rows] + [rb(rows[-1][1][k] - rows[0][1][k]),
                                                                 rows[-1][1][k] / supply * 100] for k in order]))
    fig["where"] = {k: {"start": rb(rows[0][1][k]), "end": rb(rows[-1][1][k])} for k in order}

    # ---- Who holds (positions by group) ---------------------------------------
    who = []
    for name, label, b in snaps:
        g = defaultdict(int)
        members = defaultdict(int)
        for a, v in POS[b].items():
            grp = final_group(a)
            g[grp] += v
            if v >= WEI:
                members[grp] += 1
        g["Not located"] = supply - sum(native[b].values())
        who.append((label, g, members))
    groups = sorted({k for _, g, _ in who for k in g}, key=lambda k: -who[-1][1].get(k, 0))
    groups = [k for k in groups if k != "Not located"] + ["Not located"]
    who_rows = []
    for k in groups:
        s, e = who[0][1].get(k, 0), who[-1][1].get(k, 0)
        cnt = len(group_members[k]) if k != "Not located" else ""
        if k not in ("Other wallets", "Redbelly reserved wallets", "Not located", "Reddex pools: reward funds",
                     "WRBNT contract surplus"):
            check(f"Group '{k}' has at least {min_group} members", cnt >= min_group, str(cnt))
        who_rows.append([k, cnt] + [rb(g.get(k, 0)) for _, g, _ in who] + [rb(e - s), e / supply * 100])
    out_files.append(write("03_who_holds.csv", ["group", "addresses_holding_1_rbnt_or_more_in_quarter"] + [l for l, _, _ in who] +
                           ["change_rbnt", "share_end_pct"], who_rows))
    check("Group changes add up to the change in RBNT located",
          sum(who[-1][1].values()) - sum(who[0][1].values()) == 0)
    fig["who"] = {r[0]: {"members_end": r[1], "start": r[2], "end": r[5], "change": r[6], "share_end_pct": r[7]}
                  for r in who_rows}

    # ---- Community wallets: holder counts, bands, concentration --------------
    def community(b):
        return {a: v for a, v in POS[b].items() if final_group(a) == "Other wallets"}

    COMM = {b: community(b) for b in blocks}

    band_rows = []
    for i in range(len(edges)):
        lo = edges[i]
        hi = edges[i + 1] if i + 1 < len(edges) else None
        r = {"lo": lo, "hi": hi}
        for name, label, b in snaps:
            vals = [v for v in COMM[b].values() if A.band_index(v, edges) == i]
            r[f"n:{label}"] = len(vals)
            r[f"rbnt:{label}"] = sum(vals)
        band_rows.append(r)
    # Merge on the most restrictive snapshot so bands are the same in every column.
    while True:
        small = [i for i in range(1, len(band_rows)) if min(band_rows[i][f"n:{l}"] for _, l, _ in snaps) < min_group]
        if not small:
            break
        i = small[-1]
        for k, v in band_rows[i].items():
            if k.startswith(("n:", "rbnt:")):
                band_rows[i - 1][k] += v
        band_rows[i - 1]["hi"] = band_rows[i]["hi"]
        band_rows.pop(i)
    dust = {label: sum(1 for a, v in COMM[b].items() if 0 < v < WEI) for _, label, b in snaps}
    bands_out = []
    for r in band_rows:
        lab = f"{A.fmt_rbnt_short(r['lo'])} to {A.fmt_rbnt_short(r['hi'])}" if r["hi"] else f"{A.fmt_rbnt_short(r['lo'])} and over"
        bands_out.append([lab] + [r[f"n:{l}"] for _, l, _ in snaps] + [rb(r[f"rbnt:{l}"]) for _, l, _ in snaps])
    out_files.append(write("04_holders_by_size.csv", ["band_rbnt"] + [f"wallets_{l}" for _, l, _ in snaps] +
                           [f"rbnt_{l}" for _, l, _ in snaps], bands_out))
    fig["bands"] = [{"band": r[0], "wallets_start": r[1], "wallets_end": r[4], "rbnt_start": r[5], "rbnt_end": r[8]}
                    for r in bands_out]
    fig["dust_wallets"] = dust

    conc_rows, lorenz_rows = [], []
    for name, label, b in snaps:
        vals = [v for v in COMM[b].values() if v >= WEI]
        all_vals = [v for v in POS[b].values() if v >= WEI]
        srt = sorted(vals)
        median = srt[len(srt) // 2]
        conc_rows.append([label, b, len(vals), rb(sum(vals)), A.top_share(vals, 10) * 100, A.top_share(vals, 100) * 100,
                          A.top_share(vals, 1000) * 100, A.count_to_half(vals), A.gini(vals), rb(median),
                          len(all_vals), A.top_share(all_vals, 10) * 100, A.gini(all_vals)])
    out_files.append(write("05_concentration.csv",
                           ["snapshot", "block", "wallets_1_rbnt_or_more", "rbnt_held_by_them", "top10_share_pct",
                            "top100_share_pct", "top1000_share_pct", "wallets_holding_half", "gini", "median_rbnt",
                            "all_holders_incl_named_and_contracts", "all_holders_top10_share_pct", "all_holders_gini"],
                           conc_rows))
    for (_, l0, b0), (_, l1, b1) in [(snaps[0], snaps[-1])]:
        L0 = A.lorenz([v for v in COMM[b0].values() if v >= WEI], 200)
        L1 = A.lorenz([v for v in COMM[b1].values() if v >= WEI], 200)
        lorenz_rows = [[f"{x:.3f}", f"{y0 * 100:.4f}", f"{y1 * 100:.4f}"] for (x, y0), (_, y1) in zip(L0, L1)]
    out_files.append(write("05b_lorenz_curve.csv", ["share_of_wallets", "share_of_rbnt_pct_start", "share_of_rbnt_pct_end"],
                           lorenz_rows))
    fig["concentration"] = {r[0]: {"wallets": r[2], "rbnt": r[3], "top10": r[4], "top100": r[5], "top1000": r[6],
                                   "to_half": r[7], "gini": r[8], "median": r[9]} for r in conc_rows}

    # ---- Cohorts: wallets followed from start to end ---------------------------
    start_c, end_c = COMM[S0], COMM[S1]
    thr = cfg["change_threshold"]
    cohort = []
    for r in band_rows:
        lo, hi = r["lo"] * WEI, (r["hi"] * WEI if r["hi"] else None)
        members = [a for a, v in start_c.items() if v >= lo and (hi is None or v < hi)]
        c = defaultdict(int)
        s_tot = e_tot = 0
        for a in members:
            s, e = start_c[a], end_c.get(a, 0)
            c[A.classify_change(s, e, thr)] += 1
            s_tot += s
            e_tot += e
        lab = f"{A.fmt_rbnt_short(r['lo'])} to {A.fmt_rbnt_short(r['hi'])}" if r["hi"] else f"{A.fmt_rbnt_short(r['lo'])} and over"
        cohort.append([lab, len(members), rb(s_tot), rb(e_tot), rb(e_tot - s_tot), c["added"], c["steady"],
                       c["reduced"], c["exited"]])
    new = [a for a, v in end_c.items() if v >= WEI and start_c.get(a, 0) < WEI]
    cohort.append(["New: under 1 at start", len(new), rb(sum(start_c.get(a, 0) for a in new)),
                   rb(sum(end_c[a] for a in new)), rb(sum(end_c[a] - start_c.get(a, 0) for a in new)), "", "", "", ""])
    out_files.append(write("06_cohorts.csv", ["cohort_by_start_holding", "wallets", "rbnt_start", "rbnt_end", "net_change",
                                              "added_over_1pct", "within_1pct", "reduced_over_1pct", "below_1_rbnt_at_end"],
                           cohort))
    fig["cohorts"] = [{"cohort": r[0], "wallets": r[1], "start": r[2], "end": r[3], "net": r[4], "added": r[5],
                       "steady": r[6], "reduced": r[7], "exited": r[8]} for r in cohort]

    # Band migration matrix, cells under min_group shown as "<5".
    labs = ["Under 1"] + [r[0] for r in bands_out]

    def bidx(v):
        if v < WEI:
            return 0
        for j, r in enumerate(band_rows):
            if v >= r["lo"] * WEI and (r["hi"] is None or v < r["hi"] * WEI):
                return j + 1
        return len(band_rows)

    everyone = set(start_c) | set(end_c)
    matrix = [[0] * len(labs) for _ in labs]
    for a in everyone:
        s, e = start_c.get(a, 0), end_c.get(a, 0)
        if s < WEI and e < WEI:
            continue
        matrix[bidx(s)][bidx(e)] += 1
    mrows = []
    for i, row in enumerate(matrix):
        mrows.append([labs[i]] + [(c if c >= min_group or c == 0 else f"<{min_group}") for c in row])
    out_files.append(write("06b_band_migration.csv", ["start_band \\ end_band"] + labs, mrows))
    fig["migration"] = {"labels": labs, "matrix": mrows}

    # Rank groups fixed at the start.
    ranked = sorted(start_c.items(), key=lambda x: -x[1])
    rank_rows = []
    for lo, hi in cfg["top_groups"]:
        grp = ranked[lo - 1:hi] if hi else ranked[lo - 1:]
        grp = [(a, v) for a, v in grp if v >= WEI]
        c = defaultdict(int)
        comp = {k: [0, 0] for k in ("native", "wrbnt", "staked")}
        for a, s in grp:
            c[A.classify_change(s, end_c.get(a, 0), thr)] += 1
            for k in comp:
                comp[k][0] += PARTS[S0][k].get(a, 0)
                comp[k][1] += PARTS[S1][k].get(a, 0)
        s_tot = sum(v for _, v in grp)
        e_tot = sum(end_c.get(a, 0) for a, _ in grp)
        name = f"Largest {hi}" if lo == 1 else (f"Ranks {lo:,} to {hi:,}" if hi else f"Ranks {lo:,} and below")
        rank_rows.append([name, len(grp), rb(s_tot), rb(e_tot), rb(e_tot - s_tot), A.pct(e_tot, s_tot), c["added"],
                          c["steady"], c["reduced"], c["exited"]] +
                         [rb(comp[k][i]) for k in comp for i in (0, 1)])
    out_files.append(write("06c_largest_holders.csv",
                           ["group_ranked_at_start", "wallets", "rbnt_start", "rbnt_end", "net_change", "change_pct",
                            "added_over_1pct", "within_1pct", "reduced_over_1pct", "below_1_rbnt_at_end",
                            "native_start", "native_end", "wrbnt_start", "wrbnt_end", "staked_start", "staked_end"],
                           rank_rows))
    fig["largest"] = [{"group": r[0], "wallets": r[1], "start": r[2], "end": r[3], "net": r[4], "pct": r[5],
                       "added": r[6], "steady": r[7], "reduced": r[8], "exited": r[9],
                       "staked_start": r[14], "staked_end": r[15], "wrbnt_start": r[12], "wrbnt_end": r[13]}
                      for r in rank_rows]

    # ---- Staking ------------------------------------------------------------------
    day_snaps = store.snapshots(db, "day")
    daily = []
    for name, b, ts in day_snaps:
        row = [name[4:], b]
        for p in pools:
            row += [rb(kv[f"pool_balance:{p}@{b}"]), rb(kv[f"total_stake:{p}@{b}"])]
        row += [rb(kv[f"wrbnt_supply@{b}"])]
        daily.append(row)
    dh = ["day_start_utc", "block"]
    for p in pools:
        short = "no_lock" if "no lock" in pools[p] else "365_day"
        dh += [f"{short}_pool_balance", f"{short}_total_stake"]
    out_files.append(write("07b_daily_pools_and_wrbnt.csv", dh + ["wrbnt_supply"], daily))

    sel_stake = "0x3a4b66f1"  # stake()
    pool_rows, fig["staking"] = [], {}
    logs = defaultdict(list)
    for blk, tx, idx, addr, topics, data in db.execute(
            "SELECT block, tx, idx, address, topics, data FROM logs WHERE block > ? AND block <= ?", (S0, S1)):
        logs[addr].append((blk, json.loads(topics)[0], data))
    from rbnt.rpc import sel
    T_STAKE = "0x" + sel("Stake(address,uint256,uint256,uint256)")[2:].ljust(64, "0")
    t_stake = sel("Stake(address,uint256,uint256,uint256)")
    t_unstake = sel("Unstake(address,uint256,uint256,uint256)")
    t_claim = sel("ClaimLiquidXReward(address,uint256)")
    del T_STAKE
    for p, plabel in pools.items():
        ev = defaultdict(lambda: [0, 0])
        for blk, t0, data in logs[p]:
            amt = int(data[66:130], 16) if len(data) >= 130 else 0
            for key, topic in (("stake", t_stake), ("unstake", t_unstake), ("claim", t_claim)):
                if t0.startswith(topic):
                    ev[key][0] += 1
                    ev[key][1] += amt
        # Plain transfers in that were not stake() calls: reward top ups.
        topup = sum(int(v) for (v,) in db.execute(
            "SELECT value FROM qtx WHERE recipient=? AND status=1 AND input4 != ? AND value != '0'", (p, sel_stake)))
        topup += sum(int(v) for (v,) in db.execute(
            "SELECT value FROM internal WHERE recipient=? AND is_error=0 AND type='call'", (p,)))
        k = f"stake:{p}"
        st0 = {a for a, v in token[S0][k].items() if v > 0}
        st1 = {a for a, v in token[S1][k].items() if v > 0}
        b0, b1 = kv[f"pool_balance:{p}@{S0}"], kv[f"pool_balance:{p}@{S1}"]
        s0, s1 = kv[f"total_stake:{p}@{S0}"], kv[f"total_stake:{p}@{S1}"]
        check(f"{plabel}: stakes minus unstakes equal the change in totalStake",
              ev["stake"][1] - ev["unstake"][1] == s1 - s0, f"{ev['stake'][1] - ev['unstake'][1]} vs {s1 - s0}")
        pool_rows.append([plabel, rb(b0), rb(b1), rb(b1 - b0), A.pct(b1, b0), rb(s0), rb(s1), rb(s1 - s0),
                          rb(b0 - s0), rb(b1 - s1), len(st0), len(st1), len(st1 - st0), len(st0 - st1),
                          ev["stake"][0], rb(ev["stake"][1]), ev["unstake"][0], rb(ev["unstake"][1]),
                          ev["claim"][0], rb(ev["claim"][1]), rb(topup)])
        fig["staking"][plabel] = dict(zip(
            ["balance_start", "balance_end", "balance_change", "balance_change_pct", "staked_start", "staked_end",
             "staked_change", "reward_funds_start", "reward_funds_end", "stakers_start", "stakers_end", "new_stakers",
             "left_stakers", "stake_events", "staked_in", "unstake_events", "unstaked_out", "claim_events",
             "rewards_claimed", "plain_transfers_in"], pool_rows[-1][1:]))
    out_files.append(write("07_staking_pools.csv",
                           ["pool", "balance_start", "balance_end", "balance_change", "balance_change_pct",
                            "total_stake_start", "total_stake_end", "total_stake_change", "reward_funds_start",
                            "reward_funds_end", "stakers_start", "stakers_end", "new_stakers", "stakers_who_left",
                            "stake_events", "rbnt_staked", "unstake_events", "rbnt_unstaked", "reward_claims",
                            "rbnt_rewards_claimed", "plain_transfers_in_rbnt"], pool_rows))
    tb0 = sum(r[1] for r in pool_rows)
    tb1 = sum(r[2] for r in pool_rows)
    fig["staking"]["both"] = {"balance_start": tb0, "balance_end": tb1, "change_pct": (tb1 - tb0) / tb0 * 100,
                              "staked_start": sum(r[5] for r in pool_rows), "staked_end": sum(r[6] for r in pool_rows)}
    # Share of community wallet holdings that is staked.
    for (_, label, b), key in ((snaps[0], "start"), (snaps[-1], "end")):
        comm_total = sum(COMM[b].values())
        comm_staked = sum(PARTS[b]["staked"].get(a, 0) for a in COMM[b])
        fig["staking"]["both"][f"community_staked_share_{key}"] = comm_staked / comm_total * 100

    # Staker sizes at the end, per pool.
    size_rows = []
    for p, plabel in pools.items():
        vals = [v for v in token[S1][f"stake:{p}"].values() if v > 0]
        rows_ = []
        for i in range(len(edges)):
            lo, hi = edges[i], (edges[i + 1] if i + 1 < len(edges) else None)
            sel_v = [v for v in vals if v >= lo * WEI and (hi is None or v < hi * WEI)]
            rows_.append({"lo": lo, "hi": hi, "n": len(sel_v), "amt": sum(sel_v)})
        under = [v for v in vals if v < WEI]
        if under:
            rows_[0]["n"] += len(under)
            rows_[0]["amt"] += sum(under)
            rows_[0]["lo"] = 0
        rows_ = [r for r in rows_]
        rows_ = A.merge_small(rows_, "n", min_group)
        for r in rows_:
            lab = f"{A.fmt_rbnt_short(r['lo'])} to {A.fmt_rbnt_short(r['hi'])}" if r["hi"] else f"{A.fmt_rbnt_short(r['lo'])} and over"
            if r["lo"] == 0:
                lab = f"Under {A.fmt_rbnt_short(r['hi'])}"
            size_rows.append([plabel, lab, r["n"], rb(r["amt"])])
    out_files.append(write("07c_staker_sizes_end.csv", ["pool", "stake_size_rbnt", "stakers", "rbnt_staked"], size_rows))

    # Lock calendar for every pool with a lock: RBNT unlocking per month.
    cal = defaultdict(lambda: [0, 0])
    for pool, a, amt, t in db.execute("SELECT pool, addr, amount, unlock_ts FROM unlocks"):
        if t <= int(datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp()):
            month = "Already unlocked"
        else:
            month = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m")
        cal[(pools[pool], month)][0] += 1
        cal[(pools[pool], month)][1] += int(amt)
    cal_rows = []
    for (plabel, month), (n, amt) in sorted(cal.items(), key=lambda x: (x[0][0], x[0][1] != "Already unlocked", x[0][1])):
        if "365" not in plabel:
            continue
        cal_rows.append([plabel, month, n if n >= min_group else f"<{min_group}", rb(amt)])
    lock_total = sum(int(a) for p, a in db.execute("SELECT pool, amount FROM unlocks") if "365" in pools[p])
    p365 = next(p for p in pools if "365" in pools[p])
    check("Lock calendar adds up to totalStake of the 365 day pool", lock_total == kv[f"total_stake:{p365}@{S1}"],
          f"{lock_total} vs {kv[f'total_stake:{p365}@{S1}']}")
    out_files.append(write("07d_lock_calendar_365_day.csv", ["pool", "unlock_month_utc", "open_stakes", "rbnt"], cal_rows))
    fig["lock_calendar"] = cal_rows

    # ---- Named wallets: balances, flows, reconciliation --------------------------
    named_rows, flow_rows = [], []
    kind_cache = {}

    def counterparty(a):
        if a in reserved:
            return reserved[a]
        if a in pools:
            return pools[a]
        if a == wrbnt:
            return "Wrapped RBNT contract"
        if a in exchange_labels:
            return "Labelled exchange wallets"
        if a in labels:
            return labels[a]
        if a not in code and a not in kind_cache:
            c = rpc.call("eth_getCode", [a, hex(S1)])
            kind_cache[a] = "contract" if c not in ("0x", "0x0") and not c.startswith("0xef0100") else "wallet"
        k = code.get(a) or kind_cache.get(a)
        if k == "contract":
            # Contracts are shown by the kind of program they are, a group of at least five.
            return final_group(a) if a in cnames else "Unverified contracts"
        return "Unlabelled wallets"

    named_list = [(a, reserved[a], "Reserved wallet") for a in reserved] + \
                 [(wrbnt, cfg["wrbnt"]["label"], "Wrapped RBNT")] + [(p, pools[p], "Staking pool") for p in pools]
    for a, label, cat in named_list:
        s, e = native[S0][a], native[S1][a]
        flows = defaultdict(lambda: [0, 0, 0, 0])   # in amount, in count, out amount, out count
        fees = 0
        for snd, rcp, val, fee, status in db.execute(
                "SELECT sender, recipient, value, fee, status FROM qtx WHERE sender=? OR recipient=?", (a, a)):
            if snd == a:
                fees += int(fee)
            if status != 1 or val == "0" or snd == rcp:
                continue
            if rcp == a:
                f = flows[counterparty(snd)]
                f[0] += int(val)
                f[1] += 1
            else:
                f = flows[counterparty(rcp)]
                f[2] += int(val)
                f[3] += 1
        for snd, rcp, val in db.execute("""SELECT sender, recipient, value FROM internal
                WHERE (sender=? OR recipient=?) AND is_error=0 AND type IN ('call','create','create2')""", (a, a)):
            if val == "0" or snd == rcp:
                continue
            if rcp == a:
                f = flows[counterparty(snd)]
                f[0] += int(val)
                f[1] += 1
            else:
                f = flows[counterparty(rcp)]
                f[2] += int(val)
                f[3] += 1
        tin = sum(f[0] for f in flows.values())
        tout = sum(f[2] for f in flows.values())
        gap = e - (s + tin - tout - fees)
        check(f"{label} reconciles: start + in - out - fees = end", gap == 0, f"gap {gap} wei")
        named_rows.append([cat, label, a, s / WEI, e / WEI, (e - s) / WEI, tin / WEI, tout / WEI, fees / WEI, gap])
        for cp, (ia, ic, oa, oc) in sorted(flows.items(), key=lambda x: -(x[1][0] + x[1][2])):
            flow_rows.append([label, cp, ia / WEI, ic, oa / WEI, oc])
    out_files.append(write("08_named_wallets.csv", ["category", "label", "address", "balance_start", "balance_end",
                                                    "change", "rbnt_in", "rbnt_out", "fees_paid", "reconciliation_gap_wei"],
                           named_rows))
    out_files.append(write("08b_named_wallet_flows.csv", ["named_wallet", "counterparty", "rbnt_in", "transfers_in",
                                                          "rbnt_out", "transfers_out"], flow_rows))
    fig["named"] = {r[1]: {"start": r[3], "end": r[4], "change": r[5], "in": r[6], "out": r[7], "fees": r[8]}
                    for r in named_rows}
    fig["named_flows"] = [{"wallet": r[0], "counterparty": r[1], "in": r[2], "in_n": r[3], "out": r[4], "out_n": r[5]}
                          for r in flow_rows]
    fig["labelled_exchanges"] = list(exchange_labels.values())
    fig["explorer_labels"] = list(labels.values())

    # WRBNT movements of the reserved wallets: wraps, unwraps and token transfers.
    from rbnt.rpc import sel as _sel
    T_TRANSFER = "0x" + __import__("rbnt.rpc", fromlist=["keccak"]).keccak(b"Transfer(address,address,uint256)").hex()
    T_DEPOSIT = "0x" + __import__("rbnt.rpc", fromlist=["keccak"]).keccak(b"Deposit(address,uint256)").hex()
    T_WITHDRAW = "0x" + __import__("rbnt.rpc", fromlist=["keccak"]).keccak(b"Withdrawal(address,uint256)").hex()
    wf = defaultdict(lambda: [0, 0])
    for blk, topics, data in db.execute("SELECT block, topics, data FROM logs WHERE address=? AND block > ? AND block <= ?",
                                        (wrbnt, S0, S1)):
        t = json.loads(topics)
        if t[0] == T_TRANSFER:
            f, to, v = "0x" + t[1][-40:], "0x" + t[2][-40:], int(data, 16)
            if f in reserved:
                wf[(reserved[f], "WRBNT sent", counterparty(to))][0] += v
                wf[(reserved[f], "WRBNT sent", counterparty(to))][1] += 1
            if to in reserved:
                wf[(reserved[to], "WRBNT received", counterparty(f))][0] += v
                wf[(reserved[to], "WRBNT received", counterparty(f))][1] += 1
        elif t[0] in (T_DEPOSIT, T_WITHDRAW) and "0x" + t[1][-40:] in reserved:
            k = (reserved["0x" + t[1][-40:]], "Wrapped RBNT into WRBNT" if t[0] == T_DEPOSIT else "Unwrapped WRBNT", "")
            wf[k][0] += int(data, 16)
            wf[k][1] += 1
    out_files.append(write("08d_reserved_wrbnt_flows.csv", ["reserved_wallet", "movement", "counterparty", "wrbnt",
                                                            "transfers"],
                           [[a, m, c, v / WEI, n] for (a, m, c), (v, n) in sorted(wf.items())]))
    fig["reserved_wrbnt"] = [{"wallet": a, "movement": m, "counterparty": c, "amount": v / WEI, "n": n}
                             for (a, m, c), (v, n) in sorted(wf.items())]

    # Native RBNT moved between groups during the quarter.
    def flow_group(a):
        if a in reserved:
            return "Redbelly reserved wallets"
        if a in pools:
            return "Reddex staking pools"
        if a == wrbnt:
            return "Wrapped RBNT contract"
        if a in code and code[a] == "contract":
            return final_group(a)
        if a not in code:
            k = kind_cache.get(a)
            if k is None:
                c = rpc.call("eth_getCode", [a, hex(S1)])
                k = kind_cache[a] = "contract" if c not in ("0x", "0x0") and not c.startswith("0xef0100") else "wallet"
            if k == "contract":
                return final_group(a) if a in cnames else "Unverified contracts"
        return "Other wallets"

    gflow = defaultdict(lambda: [0, 0])
    for snd, rcp, val in db.execute("SELECT sender, recipient, value FROM qtx WHERE status=1 AND value != '0'"):
        if rcp:
            gflow[(flow_group(snd), flow_group(rcp))][0] += int(val)
            gflow[(flow_group(snd), flow_group(rcp))][1] += 1
    for snd, rcp, val in db.execute("""SELECT sender, recipient, value FROM internal
            WHERE is_error=0 AND type IN ('call','create','create2') AND value != '0'"""):
        if rcp:
            gflow[(flow_group(snd), flow_group(rcp))][0] += int(val)
            gflow[(flow_group(snd), flow_group(rcp))][1] += 1
    wflow = defaultdict(lambda: [0, 0])
    for blk, topics, data in db.execute("SELECT block, topics, data FROM logs WHERE address=? AND block > ? AND block <= ?",
                                        (wrbnt, S0, S1)):
        t = json.loads(topics)
        if t[0] == T_TRANSFER:
            k = (flow_group("0x" + t[1][-40:]), flow_group("0x" + t[2][-40:]))
            wflow[k][0] += int(data, 16)
            wflow[k][1] += 1
    keys = sorted(set(gflow) | set(wflow), key=lambda k: -(gflow[k][0] + wflow[k][0]))
    out_files.append(write("09_group_flows.csv", ["from_group", "to_group", "rbnt", "rbnt_transfers", "wrbnt",
                                                  "wrbnt_transfers", "rbnt_plus_wrbnt"],
                           [[f, t, gflow[(f, t)][0] / WEI, gflow[(f, t)][1], wflow[(f, t)][0] / WEI, wflow[(f, t)][1],
                             (gflow[(f, t)][0] + wflow[(f, t)][0]) / WEI] for f, t in keys]))
    fig["group_flows"] = [{"from": f, "to": t, "rbnt": gflow[(f, t)][0] / WEI, "wrbnt": wflow[(f, t)][0] / WEI,
                           "total": (gflow[(f, t)][0] + wflow[(f, t)][0]) / WEI} for f, t in keys]

    day_rows = []
    named_days = store.snapshots(db, "day")
    bal = {(a, b): int(w) for a, b, w in db.execute("SELECT addr, block, wei FROM balance WHERE addr IN (%s)" %
                                                   ",".join("?" * len(reserved)), list(reserved))}
    for name, b, _ in named_days:
        day_rows.append([name[4:], b] + [bal[(a, b)] / WEI for a in reserved])
    out_files.append(write("08c_reserved_wallets_daily.csv", ["day_start_utc", "block"] + list(reserved.values()), day_rows))

    # ---- Fees and the network -----------------------------------------------------
    fees_q = sum(int(f) for (f,) in db.execute("SELECT fees FROM qblock"))
    fig["network"] = {"fees_paid_quarter": fees_q / WEI,
                      "transactions_quarter": db.execute("SELECT count(*) FROM qtx").fetchone()[0],
                      "addresses_scanned": db.execute("SELECT count(*) FROM addresses").fetchone()[0],
                      "blocks_scanned": S1 + 1,
                      "internal_rows": int(store.kv_get(db, "internal_rows", 0)),
                      "explorer_list_read": int(store.kv_get(db, "explorer_list_read", 0))}

    fig["checks"] = CHECKS
    fig["files"] = out_files
    path = config.data_dir("processed") / "figures.json"
    path.write_text(json.dumps(fig, indent=2, default=str) + "\n")
    print(f"{len(CHECKS)} checks passed; wrote {len(out_files)} CSV files and figures.json")


if __name__ == "__main__":
    main()
