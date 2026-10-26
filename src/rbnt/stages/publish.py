"""Write the deliverables from data/<edition>/.

index.html and how-we-did-it.html (the web edition, served from the repository
root), the PDF printed from that page, a Word file built from the same blocks,
a workbook with every table, and the community summary, thread and cards.

All numbers come from headline.json or the tables. Words that describe a
direction (grew, shrank) are chosen from the numbers, so a new edition with a
different pattern still reads correctly.
"""

import csv
import json
from html import escape

from .. import edition, outputs, site
from ..numbers import grouped, percent, plus, points, words

HOME = edition.HOME


def rows_of(name):
    with open(edition.out_dir() / name) as fh:
        return list(csv.DictReader(fh))


def went(a, b, up="rose", down="fell", level="held level"):
    return up if b > a else down if b < a else level


def run(flags):
    cfg = edition.read()
    H = json.loads((edition.out_dir() / "headline.json").read_text())
    audit_file = edition.out_dir() / "audit.json"
    A = json.loads(audit_file.read_text()) if audit_file.exists() else None
    ed, slug = cfg["edition"], cfg["edition"].lower().replace(" ", "-")
    m = H["moments"]
    T0, T1 = m["start"]["title"], m["end"]["title"]
    B0, B1 = m["start"]["block"], m["end"]["block"]
    read_on = H["read_on"]
    data_path = f"data/{edition.EDITION}"
    chain_note = (f"Redbelly mainnet (chain ID 151), eth_getBalance and eth_call at block {B0:,} "
                  f"(30 June, 23:57:19 UTC) and block {B1:,} (30 September, 23:57:35 UTC). Read {read_on}.")

    P = H["pools"]
    both, nl, ly = P["both"], P["Reddex no lock pool"], P["Reddex 365 day pool"]
    C = H["concentration"]
    c0, c1 = C[T0], C[T1]
    G = H["groups"]
    N = H["named"]
    reserved = [w["label"] for w in cfg["reserved_wallets"]["wallets"]]
    res0, res1 = sum(N[r]["start"] for r in reserved), sum(N[r]["end"] for r in reserved)
    wr0, wr1 = N[cfg["wrbnt"]["label"]]["start"], N[cfg["wrbnt"]["label"]]["end"]
    ranks = {r["group"]: r for r in H["ranks"]}
    t10, n90 = ranks["Top 10"], ranks["Next 90"]
    top100 = {k: t10[k] + n90[k] for k in ("start", "end", "up", "flat", "down", "emptied", "staked_start", "staked_end")}
    cohorts = H["cohorts"]
    arrivals = cohorts[-1]
    emptied = sum(c["emptied"] for c in cohorts[:-1])
    vest = G.get("Token vesting contracts", {"start": 0, "end": 0})
    gf = H["group_flows"]
    vest_out = sum(f["together"] for f in gf if f["from"] == "Token vesting contracts" and f["to"] == "Unnamed wallets")
    vest_n = sum(f["transfers"] for f in gf if f["from"] == "Token vesting contracts" and f["to"] == "Unnamed wallets")
    flow = lambda a, b: sum(f["together"] for f in gf if f["from"] == a and f["to"] == b)
    cp = H["counterparties"]
    res_set = set(reserved)
    inside = sorted([f for f in cp if f["wallet"] in res_set and f["party"] in res_set and f["out"] > 0],
                    key=lambda f: -f["out"])
    outside = {}
    for f in cp:
        if f["wallet"] in res_set and f["party"] not in res_set and f["out"] > 0:
            outside.setdefault(f["wallet"], []).append(f)
    inside_total = sum(f["out"] for f in inside)
    sup = H["supply"]
    work = H["chain_work"]

    # ---- Opening and findings ----------------------------------------------------------
    top = {
        "overline": f"Redbelly DAO · on-chain holder report · edition 1",
        "title": "RBNT holders, July to September 2026",
        "sub": ("What the 10 billion RBNT did over one quarter: who holds them, how spread out they are, what the "
                "biggest wallets did, how much is staked with Reddex, and what moved in and out of the wallets "
                "with public names. Every figure comes from the Redbelly chain itself."),
        "blocks": f"Compared at block {B0:,} (end of 30 June) and block {B1:,} (end of 30 September), chain ID 151.",
        "board_head": ("30 Jun", "30 Sep"),
        "board": [
            ["RBNT in the Reddex pools", words(both["rbnt_start"]), words(both["rbnt_end"]),
             plus(both["change_pct"], percent)],
            ["Wallets holding 1 RBNT or more", grouped(c0["wallets"]), grouped(c1["wallets"]),
             plus(c1["wallets"] - c0["wallets"])],
            ["Share held by the 100 largest wallets", percent(c0["top100"]), percent(c1["top100"]),
             points(c1["top100"] - c0["top100"])],
            ["RBNT in the 9 reserved wallets", words(res0), words(res1), plus(res1 - res0, words)],
            ["WRBNT in circulation", words(wr0), words(wr1), plus(wr1 - wr0, words)],
            ["Held by token vesting contracts", words(vest["start"]), words(vest["end"]),
             plus(vest["end"] - vest["start"], words)],
        ],
        "checked": (f"{len(H['checks'])} exact checks held when the tables were built. "
                    + (f"Re-read from the node on {A['ran']}: {A['passed']} of {A['passed'] + A['failed']} checks passed."
                       if A else "")),
    }

    findings = [
        (plus(both["change_pct"], percent), f"Staking {went(both['rbnt_start'], both['rbnt_end'], 'grew', 'shrank')}",
         f"We counted <b>{words(both['rbnt_end'])} RBNT</b> in the two Reddex pools at the end of September, "
         f"{words(abs(both['rbnt_end'] - both['rbnt_start']))} {'more' if both['rbnt_end'] >= both['rbnt_start'] else 'less'} "
         f"than at the end of June. The no lock pool took {words(nl['rbnt_change'])} of that change. "
         f"Open stakers: {grouped(nl['stakers_start'])} to {grouped(nl['stakers_end'])} in the no lock pool, "
         f"{grouped(ly['stakers_start'])} to {grouped(ly['stakers_end'])} in the 365 day pool."),
        (words(vest_out), "Vesting contracts paid out",
         f"The {grouped(G['Token vesting contracts']['members'])} contracts whose published code is a token vesting "
         f"manager sent {words(vest_out)} WRBNT to unnamed wallets in {grouped(vest_n)} transfers. Together they went "
         f"from {words(vest['start'])} to {words(vest['end'])}."),
        (words(inside_total), "Reserved wallets reshuffled among themselves",
         "Three moves inside the reserved group: " + "; ".join(
             f"{f['wallet']} to {f['party']}, {words(f['out'])}" for f in inside) + ". "
         + " ".join(f"{w} was the only one to send RBNT outside the group ({words(sum(x['out'] for x in fs))}), "
                    f"mostly into WRBNT and the pools' reward reserves." for w, fs in outside.items())),
        (plus(top100["end"] - top100["start"], words), "The biggest wallets ended up with more",
         f"We ranked unnamed wallets on 30 June and followed the top 100. They held {words(top100['start'])} RBNT "
         f"then (wrapped and staked included) and {words(top100['end'])} on 30 September. {top100['up']} grew by over "
         f"1%, {top100['flat']} stayed within 1% and {top100['down'] + top100['emptied']} shrank by over 1%."),
        (percent(c1["top10"]), "Holdings stayed top-heavy",
         f"The ten largest wallets hold {percent(c1['top10'])} of everything unnamed wallets hold, up from "
         f"{percent(c0['top10'])}. The largest 1% of wallets ({grouped(c1['wallets'] // 100)} of them) hold "
         f"{percent(c1['top1pct'])}. A typical wallet, the one in the middle, holds {words(c1['median'])} RBNT."),
        (plus(c1["wallets"] - c0["wallets"]), "A few more holders",
         f"{grouped(c1['wallets'])} wallets held at least 1 RBNT on 30 September against {grouped(c0['wallets'])} "
         f"on 30 June. Behind that net figure, {grouped(arrivals['wallets'])} wallets rose past 1 RBNT and "
         f"{grouped(emptied)} dropped under it."),
    ]

    blocks = [
        ("chapter", "00", "What the quarter looked like", "findings", "Findings"),
        ("findings", findings),
        ("rules", [
            ("Public names only", "Twelve addresses are named: the nine reserved wallets published by the DAO, the WRBNT "
                                  "contract and Reddex's two RBNT pools. "
                                  + ("The explorer tags no exchange wallet, so we name none."
                                     if not H["exchange_tags"] else "Explorer-tagged exchanges are named too.")),
            ("Groups of five or more", "Every other address is only ever part of a count or a total, in a group with at "
                                       "least four others. No address outside the named list appears anywhere."),
            ("What, not why", "The chain shows coins moving between addresses. It cannot show who is behind an "
                              "address or the reason for a move. We forecast nothing and advise nothing."),
        ]),
        ("terms", [
            ("Address", "A public account on the chain. Anyone can look up what it holds."),
            ("Wallet or contract", "A wallet is opened with a private key held by a person or an organisation. A "
                                   "contract is a program that holds and moves coins by fixed rules."),
            ("Holding", "Everything an address owns: RBNT, plus WRBNT, plus RBNT it has staked. Wrapped and staked coins "
                        "are counted once, with their owner, and never again at the contract."),
        ]),
    ]

    # ---- 01 The 10 billion ---------------------------------------------------------------
    hold_rows = rows_of("holdings_by_group.csv")
    place_rows = rows_of("location_by_place.csv")
    contracts_end = sum(v["end"] for k, v in G.items() if k not in
                        ("Redbelly reserved wallets", "Unnamed wallets", "Not reached by the scan",
                         "Reward reserve in the Reddex pools", "Excess RBNT in the WRBNT contract"))
    blocks += [
        ("chapter", "01", "The 10 billion, group by group", "groups", "The 10 billion"),
        ("lead", f"At the end of September Redbelly's reserved wallets held {percent(G['Redbelly reserved wallets']['share_end_pct'])} "
                 f"of all RBNT. Unnamed wallets held {percent(G['Unnamed wallets']['share_end_pct'])} and contracts "
                 f"outside the named list {percent(contracts_end / 1e8)}, most of it in token vesting contracts."),
        ("text", "Every RBNT that exists was minted when the network launched, so the total never changes. What changes "
                 "is where the coins are. In chart [[v01_holders]] each holding is credited to its owner, so RBNT that a "
                 "wallet has wrapped or staked still counts as that wallet's."),
        ("chart", 0, "Who holds the 10 billion RBNT", "Share of all RBNT by kind of owner, 30 June and 30 September.",
         "v01_holders", chain_note, f"{data_path}/holdings_by_group.csv",
         (["Group", "Addresses (1+ RBNT)", T0, T1, "Change", "Share at end"],
          [[r["group"], r["addresses_with_1_rbnt_or_more_in_quarter"], grouped(float(r[T0])), grouped(float(r[T1])),
            plus(float(r["change"])), percent(float(r["share_at_end_pct"]), 2)] for r in hold_rows], {1, 2, 3, 4, 5})),
        ("aside", "How we sort contracts",
         "When a contract's author publishes its source code on the explorer, the code carries a name such as "
         "TokenVestingManager or GnosisSafe. We use that name to put the contract in a broad kind, and we only "
         "show a kind when at least five contracts share it. A token vesting contract releases coins to fixed "
         "recipients on a timetable. A shared-key wallet (Safe) needs several keys to approve a payment. An exchange "
         "liquidity pool is the stock of coins people swap against on a decentralised exchange."),
        ("h3", "Counting by the address that holds the coins"),
        ("text", "Chart [[v02_places]] adds up the same coins differently: by the address that physically holds them. "
                 "Here the WRBNT contract and the two pools show up as places, because that is where wrapped and "
                 "staked RBNT actually sit."),
        ("chart", 0, "Where the coins sit, by the address that holds them",
         "Share of all RBNT by holding address, 30 June and 30 September.", "v02_places", chain_note,
         f"{data_path}/location_by_place.csv",
         (["Place", T0, T1, "Change", "Share at end"],
          [[r["place"], grouped(float(r[T0])), grouped(float(r[T1])), plus(float(r["change"])),
            percent(float(r["share_at_end_pct"]), 2)] for r in place_rows])),
        ("aside", "Did we find every coin?",
         f"Yes, to within {grouped(sup['not_reached_end'])} RBNT: the balances we read add up to "
         f"{percent(sup['found_pct_end'], 4)} of the supply on 30 September. The rest sits at addresses that never "
         f"took part in any transaction, internal transfer or block header we read, most likely funded at launch and "
         f"never touched. That amount moved by {grouped(abs(sup['not_reached_end'] - sup['not_reached_start']))} RBNT "
         f"over the quarter, far too little to affect any trend."),
        ("h3", "Where the coins went during the quarter"),
        ("text", f"Chart [[v15_group_flows]] traces every transfer of RBNT and WRBNT between groups from 1 July to 30 "
                 f"September. The four biggest streams were stakes from wallets into the pools "
                 f"({words(flow('Unnamed wallets', 'Reddex staking pools'))}), WRBNT from vesting contracts to wallets "
                 f"({words(vest_out)}), RBNT leaving the WRBNT contract as wallets unwrapped "
                 f"({words(flow('WRBNT contract', 'Unnamed wallets'))}), and withdrawals plus rewards paid out of the "
                 f"pools ({words(flow('Reddex staking pools', 'Unnamed wallets'))}). Moves inside one group are kept "
                 "out of the picture and listed in the table."),
        ("chart", 0, "RBNT and WRBNT moved between groups",
         "Sending group on the left, receiving group on the right; ribbon width is the amount. Ribbons under 1 million "
         "are left out of the picture but kept in the table.", "v15_group_flows",
         f"every successful transaction and internal transfer with value, and every WRBNT Transfer event, from block "
         f"{B0 + 1:,} to {B1:,}.", f"{data_path}/group_flows.csv",
         (["From", "To", "RBNT", "Transfers", "WRBNT", "Transfers", "Both"],
          [[r["from_group"], r["to_group"], grouped(float(r["rbnt"])), grouped(int(r["rbnt_transfers"])),
            grouped(float(r["wrbnt"])), grouped(int(r["wrbnt_transfers"])), grouped(float(r["together"]))]
           for r in rows_of("group_flows.csv")], {2, 3, 4, 5, 6})),
    ]

    # ---- 02 Holders by size ---------------------------------------------------------------
    bands = rows_of("size_bands.csv")
    titles = [x["title"] for x in m.values()]
    small, large = H["bands"][0], H["bands"][-1]
    blocks += [
        ("chapter", "02", "Big and small holders", "sizes", "Holder sizes"),
        ("lead", f"{grouped(c1['wallets'])} wallets held 1 RBNT or more at the end of September. "
                 f"{percent(small['wallets_end'] / c1['wallets'] * 100, 0)} of them hold under 100 RBNT, while "
                 f"{grouped(large['wallets_end'])} wallets with {large['band']} RBNT hold "
                 f"{percent(large['rbnt_end'] / c1['rbnt'] * 100, 0)} of the total."),
        ("text", f"These counts cover unnamed wallets only. Reserved wallets and contracts are left out because they are "
                 f"large by design and would drown out everyone else. Wallets with less than 1 RBNT are left out too: "
                 f"there were {grouped(H['dust_wallets'][T1])} of them on 30 September, mostly holding fee change."),
        ("chart", 0, "Share of wallets and share of wallet RBNT, by holding size",
         "For each size on 30 September: the slate dot is the share of wallets, the red dot the share of RBNT.",
         "v03_size_shares", chain_note, f"{data_path}/size_bands.csv",
         (["Holding (RBNT)"] + [f"Wallets {t}" for t in titles] + [f"RBNT {t}" for t in titles],
          [[b["holding_rbnt"]] + [grouped(int(b[f"wallets {t}"])) for t in titles] +
           [grouped(float(b[f"rbnt {t}"])) for t in titles] for b in bands])),
        ("chart", 0, "Change in wallets per holding size", "Wallets in each size on 30 September minus 30 June.",
         "v04_size_change", chain_note, f"{data_path}/size_bands.csv", None),
    ]

    # ---- 03 Concentration -------------------------------------------------------------------
    conc_rows = rows_of("concentration_measures.csv")
    blocks += [
        ("chapter", "03", "How top-heavy is it?", "concentration", "Concentration"),
        ("lead", f"Very. The ten largest wallets hold {percent(c1['top10'])} of all RBNT in unnamed wallets and the "
                 f"hundred largest {percent(c1['top100'])}. Both shares {went(c0['top100'], c1['top100'], 'edged up', 'edged down')} "
                 f"over the quarter."),
        ("text", "We use four yardsticks, all over unnamed wallets with at least 1 RBNT: the share of the largest 10, 100 "
                 "and 1,000 wallets; the share of the largest 1% of wallets; how few wallets it takes to hold more than "
                 "half; and the Gini index, a single score where 0 would mean every wallet holds the same and 1 that "
                 "one wallet holds it all."),
        ("grid", ["Yardstick"] + titles,
         [["Wallets with 1 RBNT or more"] + [grouped(int(r["wallets_with_1_rbnt_or_more"])) for r in conc_rows],
          ["RBNT those wallets hold"] + [grouped(float(r["rbnt_they_hold"])) for r in conc_rows],
          ["Largest 10 wallets"] + [percent(float(r["top_10_pct"])) for r in conc_rows],
          ["Largest 100 wallets"] + [percent(float(r["top_100_pct"])) for r in conc_rows],
          ["Largest 1,000 wallets"] + [percent(float(r["top_1000_pct"])) for r in conc_rows],
          ["Largest 1% of wallets"] + [percent(float(r["top_1_percent_of_wallets_pct"])) for r in conc_rows],
          ["Fewest wallets holding over half"] + [grouped(int(r["wallets_holding_half"])) for r in conc_rows],
          ["Gini index"] + [f"{float(r['gini']):.4f}" for r in conc_rows],
          ["Middle wallet (median), RBNT"] + [f"{float(r['median_rbnt']):,.2f}" for r in conc_rows]]),
        ("chart", 0, "How wallet RBNT splits by rank",
         "All RBNT in unnamed wallets with 1 RBNT or more, split into the top 10, the next 90, the next 900 and the rest. "
         f"The Lorenz curve points are in {data_path}/lorenz_points.csv.", "v05_concentration", chain_note,
         f"{data_path}/concentration_measures.csv", None),
        ("aside", "Reading this carefully",
         "A top-heavy spread means a small set of addresses could move a large part of the supply. It says nothing "
         "about who those addresses belong to. An exchange can keep the coins of thousands of people in one wallet, "
         "and one person can spread coins over many wallets."),
    ]

    # ---- 04 Largest holders ------------------------------------------------------------------
    co_rows = rows_of("cohort_outcomes.csv")
    rk_rows = rows_of("rank_groups.csv")
    tr = H["transitions"]
    biggest = cohorts[-2]
    blocks += [
        ("chapter", "04", "Did the big wallets add or cut?", "largest", "Largest holders"),
        ("lead", f"On balance they added. The {grouped(biggest['wallets'])} wallets that held {biggest['cohort']} RBNT "
                 f"on 30 June had {words(biggest['start'])} between them then and {words(biggest['end'])} three months "
                 f"later; {biggest['up']} of them grew, {biggest['flat']} held flat and {biggest['down']} shrank."),
        ("text", "We never follow a single wallet. Instead we sort wallets into groups by what they held on 30 June, keep "
                 "each group fixed, and count what its members held on 30 September. A wallet counts as <b>up</b> if its "
                 "holding grew by more than 1%, <b>down</b> if it shrank by more than 1%, and <b>flat</b> in between. "
                 "Staking or wrapping coins is not a fall, since the holding includes both."),
        ("chart", 0, "Outcome for each wallet, grouped by its holding on 30 June",
         "Share of each group that went up, stayed flat, went down or fell under 1 RBNT.", "v06_outcomes", chain_note,
         f"{data_path}/cohort_outcomes.csv",
         (["Holding on 30 June", "Wallets", f"RBNT {T0}", f"RBNT {T1}", "Net", "Up", "Flat", "Down", "Under 1 at end"],
          [[r["holding_on_30_june"], grouped(int(r["wallets"])), grouped(float(r["rbnt_start"])),
            grouped(float(r["rbnt_end"])), plus(float(r["net"])), r["up_more_than_1pct"], r["flat_within_1pct"],
            r["down_more_than_1pct"], r["fell_below_1_rbnt"]] for r in co_rows])),
        ("chart", 0, "Net change in RBNT for each group",
         "Total held by each group on 30 September minus 30 June. The last row is wallets that started under 1 RBNT.",
         "v07_cohort_net", chain_note, f"{data_path}/cohort_outcomes.csv", None),
        ("text", "A word of caution on the small groups: their net change can be driven by a handful of wallets that "
                 "jumped several sizes in one quarter. The movement table further down shows how many wallets changed "
                 "size, and in which direction."),
        ("h3", "The top 10, the next 90 and the next 900"),
        ("text", f"Ranking unnamed wallets by holding on 30 June gives a second view. The top 10 "
                 f"{went(t10['start'], t10['end'], 'grew', 'shrank')} by {words(abs(t10['net']))} RBNT and the next 90 by "
                 f"{words(abs(n90['net']))}. The RBNT the top 100 keep staked with Reddex "
                 f"{went(top100['staked_start'], top100['staked_end'])} by "
                 f"{words(abs(top100['staked_end'] - top100['staked_start']))}."),
        ("grid", ["Ranked on 30 June", "Wallets", f"RBNT {T0}", f"RBNT {T1}", "Net", "Change", "Up", "Flat", "Down",
                  "Under 1 at end"],
         [[r["group_ranked_on_30_june"], grouped(int(r["wallets"])), grouped(float(r["rbnt_start"])),
           grouped(float(r["rbnt_end"])), plus(float(r["net"])), plus(float(r["change_pct"]), percent),
           r["up_more_than_1pct"], r["flat_within_1pct"], r["down_more_than_1pct"], r["fell_below_1_rbnt"]]
          for r in rk_rows]),
        ("chart", 0, "How the largest wallets hold their RBNT",
         "Holdings of each rank group split into RBNT kept in the wallet, wrapped as WRBNT, and staked with Reddex.",
         "v08_rank_mix", chain_note, f"{data_path}/rank_groups.csv", None),
        ("h3", "Wallets that changed size"),
        ("text", "Rows are the size a wallet had on 30 June, columns the size on 30 September. The shaded diagonal is "
                 "wallets that stayed in the same size. Any cell with fewer than five wallets shows &lt;5."),
        ("raw", moves_table(tr), ("grid", ["On 30 June / on 30 September"] + tr["labels"],
                                  [[str(c) for c in row] for row in tr["grid"]])),
    ]

    # ---- 05 Staking ---------------------------------------------------------------------------
    pool_rows = rows_of("pools_summary.csv")
    sizes = rows_of("stake_size_bands.csv")
    sched = rows_of("unlock_schedule_365.csv")
    future = [s for s in sched if s["unlock_month_utc"][:1].isdigit()]
    past_lock = sum(float(s["rbnt"]) for s in sched if not s["unlock_month_utc"][:1].isdigit())
    soon = sum(float(s["rbnt"]) for s in future[:3])
    topups = sum(v["top_ups"] for k, v in P.items() if k != "both")
    blocks += [
        ("chapter", "05", "Staking in Reddex", "staking", "Staking"),
        ("lead", f"{went(both['rbnt_start'], both['rbnt_end'], 'Up', 'Down', 'Flat')} {percent(abs(both['change_pct']))}: "
                 f"the two Reddex pools held {words(both['rbnt_start'])} RBNT on 30 June and {words(both['rbnt_end'])} on "
                 f"30 September."),
        ("text", "Reddex runs two pools for RBNT. In the <b>no lock</b> pool a staker can take coins back at any time. In "
                 "the <b>365 day</b> pool each deposit stays put for a year from the day it was made. Following the brief, "
                 "our headline numbers are the RBNT each pool held at the two dates."),
        ("aside", "Why a pool's balance is not all stakes",
         "Stakers are paid their rewards in RBNT straight out of the pool's own coins. So a pool's balance is two "
         "things mixed together: what stakers put in, and a reserve kept for paying rewards. The pool contract keeps "
         "its own running total of stakes, called totalStake. Subtracting it from the balance gives the reward reserve, "
         "and we show both."),
        ("grid", ["Pool", f"RBNT {T0}", f"RBNT {T1}", "Change", f"Staked {T0}", f"Staked {T1}",
                  f"Reward reserve {T0}", f"Reward reserve {T1}"],
         [[r["pool"], grouped(float(r["rbnt_start"])), grouped(float(r["rbnt_end"])),
           plus(float(r["rbnt_change_pct"]), percent), grouped(float(r["total_stake_start"])),
           grouped(float(r["total_stake_end"])), grouped(float(r["reward_reserve_start"])),
           grouped(float(r["reward_reserve_end"]))] for r in pool_rows]),
        ("chart", 0, "RBNT in the two Reddex pools, daily", "Combined balance of both pools at the end of each day.",
         "v09_pools_both", f"daily snapshots, each the last block before 00:00 UTC. {chain_note}",
         f"{data_path}/pools_daily.csv", None),
        ("chart", 0, "No lock pool, daily",
         "Red: RBNT in the pool. Slate: staked RBNT (totalStake). The shaded gap between them is the reward reserve.",
         "v10_no_lock", "daily snapshots, each the last block before 00:00 UTC.", f"{data_path}/pools_daily.csv", None),
        ("chart", 0, "365 day pool, daily",
         "Red: RBNT in the pool. Slate: staked RBNT (totalStake). The shaded gap between them is the reward reserve.",
         "v10_lock_365", "daily snapshots, each the last block before 00:00 UTC.", f"{data_path}/pools_daily.csv", None),
        ("h3", "Stakers, in groups"),
        ("grid", ["Pool", f"Stakers {T0}", f"Stakers {T1}", "Joined", "Left", "Stakes", "RBNT staked", "Withdrawals",
                  "RBNT withdrawn", "Reward claims", "Rewards paid", "Top-ups"],
         [[r["pool"], grouped(int(r["stakers_start"])), grouped(int(r["stakers_end"])), grouped(int(r["stakers_joined"])),
           grouped(int(r["stakers_left"])), grouped(int(r["stake_records"])), grouped(float(r["rbnt_staked"])),
           grouped(int(r["unstake_records"])), grouped(float(r["rbnt_unstaked"])), grouped(int(r["reward_claims"])),
           grouped(float(r["rbnt_rewards_paid"])), grouped(float(r["plain_transfers_in"]))] for r in pool_rows]),
        ("text", f"Stakes and withdrawals come from each pool's own Stake and Unstake events, and for both pools the "
                 f"stakes minus the withdrawals match the change in totalStake exactly. Top-ups are plain transfers into "
                 f"a pool that were not stakes; all {words(topups)} RBNT of them came from a reserved wallet (see chapter 06). "
                 f"Measured against everything unnamed wallets hold, the staked share went from "
                 f"{percent(both['wallet_share_staked_start'])} to {percent(both['wallet_share_staked_end'])}."),
        ("grid", ["Pool", "Stake size (RBNT)", "Stakers", "RBNT staked"],
         [[r["pool"], r["stake_rbnt"], grouped(int(r["stakers"])), grouped(float(r["rbnt_staked"]))] for r in sizes],
         {2, 3}),
        ("h3", "When the locked coins come free"),
        ("text", f"Chart [[v12_unlocks]] shows, month by month, when RBNT still locked in the 365 day pool on 30 "
                 f"September reaches the end of its year. Coming free is not the same as leaving: stakers may keep the "
                 f"coins in the pool. {words(soon)} RBNT comes free in October, November and December, and another "
                 f"{words(past_lock)} was already past its lock on 30 September but still staked."),
        ("chart", 0, "Monthly unlocks in the 365 day pool",
         "RBNT still staked on 30 September, by the month (UTC) its lock ends.", "v12_unlocks",
         f"getStakeUnlockTimes for every open stake, read at block {B1:,}.", f"{data_path}/unlock_schedule_365.csv",
         (["Unlock month", "Open stakes", "RBNT"], [[s["unlock_month_utc"], s["open_stakes"], grouped(float(s["rbnt"]))]
                                                     for s in sched])),
    ]

    # ---- 06 Named wallets ---------------------------------------------------------------------
    nb = rows_of("named_balances.csv")
    nc = rows_of("named_counterparties.csv")
    tags_line = (f"The explorer shows a public name on just one of the {grouped(work['explorer_rows_read'])} largest "
                 f"addresses we read from its list: {', '.join(H['all_tags'])}. It tags no exchange wallet, so we name "
                 f"none." if not H["exchange_tags"] else f"Exchange wallets tagged by the explorer: {', '.join(H['exchange_tags'])}.")
    ecosystem_lines = []
    for w, fs in outside.items():
        get = lambda p: sum(f["out"] for f in fs if f["party"] == p)
        pools_sent = sum(f["out"] for f in fs if "pool" in f["party"])
        wallets_sent = [f for f in fs if f["party"] == "Unnamed wallets"]
        other = sum(f["out"] for f in fs) - get("WRBNT contract") - pools_sent - sum(f["out"] for f in wallets_sent)
        ecosystem_lines.append(
            f"<b>{w}</b> sent {words(get('WRBNT contract'))} into the WRBNT contract, which wraps it; "
            f"{words(pools_sent)} to the two Reddex pools as plain transfers, which tops up their reward reserves; "
            + (f"{words(sum(f['out'] for f in wallets_sent))} to unnamed wallets in "
               f"{grouped(sum(f['out_n'] for f in wallets_sent))} transfers; " if wallets_sent else "")
            + f"and {words(other)} to other contracts.")
    for w in sorted({r["wallet"] for r in H["reserved_wrbnt"]}):
        bits = []
        for r in [x for x in H["reserved_wrbnt"] if x["wallet"] == w]:
            n = f"{grouped(r['n'])} {'transfer' if r['n'] == 1 else 'transfers'}"
            if r["movement"] == "Wrapped RBNT":
                bits.append(f"wrapped {words(r['amount'])} RBNT ({n})")
            elif r["movement"] == "Unwrapped WRBNT":
                bits.append(f"unwrapped {words(r['amount'])} WRBNT ({n})")
            elif "sent" in r["movement"]:
                bits.append(f"passed {words(r['amount'])} WRBNT to {r['party'].lower()} ({n})")
            else:
                bits.append(f"got {words(r['amount'])} WRBNT back from {r['party'].lower()} ({n})")
        ecosystem_lines.append(f"<b>{w}</b>, in WRBNT: " + ", ".join(bits[:-1]) + (" and " if len(bits) > 1 else "")
                               + bits[-1] + ".")
    still = [w for w in reserved if N[w]["in"] == 0 and N[w]["out"] == 0]
    blocks += [
        ("chapter", "06", "Wallets with public names", "named", "Named wallets"),
        ("lead", f"The nine reserved wallets held {words(res1)} RBNT at the end of September, against {words(res0)} at the "
                 f"end of June. {words(inside_total)} of what they moved went from one reserved wallet to another."),
        ("text", "The DAO treasury page lists each reserved wallet with its address and the amount it was first given. "
                 "Those amounts are starting allocations, not today's holdings, so every balance here is read from the "
                 "chain. For each wallet we add up every transfer in and out during the quarter and check the sum to the "
                 "wei: opening balance, plus everything received, minus everything sent, minus fees, equals the closing "
                 "balance."),
        ("chart", 0, "Change in each reserved wallet over the quarter", "Balance on 30 September minus 30 June.",
         "v13_reserved_change", chain_note, f"{data_path}/named_balances.csv", None),
        ("grid", ["Named wallet", T0, T1, "Change", "In", "Out", "Fees"],
         [[f'{escape(r["name"])}<br><code>{r["address"]}</code>', grouped(float(r["rbnt_start"])),
           grouped(float(r["rbnt_end"])), plus(float(r["change"])), grouped(float(r["rbnt_in"])),
           grouped(float(r["rbnt_out"])), f"{float(r['fees']):,.2f}"] for r in nb]),
        ("chart", 0, "RBNT sent by reserved wallets",
         "Reserved wallet on the left, receiver on the right. Transfers under 100,000 RBNT are left out of the picture "
         "but kept in the table.", "v14_reserved_flows",
         "every transaction and internal transfer of each reserved wallet between the two snapshot blocks.",
         f"{data_path}/named_counterparties.csv",
         (["Named wallet", "Counterparty", "In", "Transfers in", "Out", "Transfers out"],
          [[r["named_wallet"], r["counterparty"], grouped(float(r["rbnt_in"])), r["transfers_in"],
            grouped(float(r["rbnt_out"])), r["transfers_out"]] for r in nc if r["named_wallet"] in res_set])),
        ("h3", "Every move, largest first"),
        ("bullets", [f"{words(f['out'])} RBNT went from <b>{f['wallet']}</b> to <b>{f['party']}</b>." for f in inside]
         + ecosystem_lines + ([f"No transfer touched {', '.join(still[:-1])} or {still[-1]} during the quarter; their balances are the same "
             f"on both dates."] if len(still) > 1 else [])),
        ("text", "WRBNT is a token, so passing it on does not change a wallet's RBNT balance in the table above. We list "
                 "it anyway so that every movement of the reserved wallets is on the page."),
        ("h3", "Exchanges and other tagged addresses"),
        ("text", tags_line + " Any counterparty without a public name shows up only as a group: unnamed wallets, or "
                             "contracts by kind."),
        ("h3", "Wrapped RBNT"),
        ("text", f"WRBNT is RBNT packaged as a token so that apps built for tokens can use it. The WRBNT contract keeps "
                 f"one RBNT for each WRBNT in circulation; we checked this held at every snapshot. Over the quarter the "
                 f"amount of WRBNT outstanding went from {words(wr0)} to {words(wr1)}, a change of {plus(wr1 - wr0, words)}."),
        ("chart", 0, "WRBNT supply, daily", "totalSupply of the WRBNT contract at the end of each day.", "v16_wrbnt",
         "WRBNT totalSupply() at the daily snapshot blocks.", f"{data_path}/pools_daily.csv", None),
    ]

    # ---- 07 How we did it ----------------------------------------------------------------------
    try_it = (
        "# RBNT held by the Reserve wallet at the end of the quarter (answer in wei, divide by 10^18)\n"
        f"curl -s {cfg['chain']['rpc_url']} -H 'content-type: application/json' \\\n"
        f"  -d '{{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getBalance\","
        f"\"params\":[\"{cfg['reserved_wallets']['wallets'][5]['address']}\",\"{hex(B1)}\"]}}'\n\n"
        "# Staked RBNT (totalStake) in the 365 day pool at the end of the quarter\n"
        f"curl -s {cfg['chain']['rpc_url']} -H 'content-type: application/json' \\\n"
        f"  -d '{{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\","
        f"\"params\":[{{\"to\":\"{cfg['staking_pools'][1]['address']}\",\"data\":\"0x8b0e9f3f\"}},\"{hex(B1)}\"]}}'")
    blocks += [
        ("chapter", "07", "How we did it", "method", "Method"),
        ("lead", "We read the whole chain ourselves, took every balance at fixed blocks, and had a second program read "
                 "the published numbers back from the node before release."),
        ("bullets", [
            f"<b>Fixed blocks.</b> Each date stands for the newest block stamped before midnight UTC: block {B0:,} for "
            f"the end of 30 June and block {B1:,} for the end of 30 September. Month ends and every day of the quarter "
            f"follow the same rule.",
            f"<b>The whole chain.</b> We read all {grouped(work['blocks_read'])} blocks from launch to the end block and "
            f"{grouped(work['inner_transfer_rows'])} internal transfers, which turned up {grouped(work['addresses_found'])} "
            f"addresses that could hold RBNT.",
            "<b>Balances from the node.</b> For each address we read RBNT, WRBNT and staked RBNT at the snapshot blocks. "
            "We never use the balances shown in the explorer's lists, which are current and rounded.",
            f"<b>Exact checks.</b> {len(H['checks'])} checks must hold to the wei before any table is written, among them: "
            "the WRBNT supply equals the sum of all WRBNT balances; each pool's stakers add up to its totalStake; stakes "
            "minus withdrawals equal the change in totalStake; every group adds back to the coins found; every named "
            "wallet balances to the last wei.",
            "<b>A second read.</b> After the tables are built, a separate stage reads every named balance, both pools' "
            "totalStake and the WRBNT supply again straight from the node, plus 600 balances picked at random, and "
            "scans every published file for any address outside the named list.",
        ]),
        ("tryit", "Paste either command into a terminal to read a figure from this report directly from the chain.", try_it),
        ("text", "The full method, the list of sources and the steps for the next edition are on "
                 "<a href=\"how-we-did-it.html\">How we did it</a>. The code that produced every number sits in the same "
                 "repository as this page."),
        ("h3", "What the chain cannot tell us"),
        ("bullets", [
            "Who controls an address, or why coins moved. A group's holdings can fall because someone sold, moved coins "
            "to another address of their own, or put them into a contract.",
            "How many people there are. Counts here are counts of addresses: one person can run many, and one exchange "
            "address can hold coins for many people.",
            "The node we read cannot replay contract calls, so coins that contracts pass along inside a transaction "
            "were taken from the explorer's records. They hold up: the named wallets, the WRBNT contract and both pools "
            "pay out mostly that way, and every one of them balances to the wei.",
            f"Public tags were read for the {grouped(work['explorer_rows_read'])} largest addresses in the explorer's "
            "list. A tag on a smaller address would not be seen.",
        ]),
    ]

    # ---- Files and glossary ----------------------------------------------------------------------
    titles_ = {
        "supply_reconciliation.csv": "Supply and backing checks", "location_by_place.csv": "Coins by holding address",
        "holdings_by_group.csv": "Holdings by group", "size_bands.csv": "Wallets by holding size",
        "concentration_measures.csv": "Concentration yardsticks", "lorenz_points.csv": "Lorenz curve points",
        "cohort_outcomes.csv": "Outcomes by starting size", "band_transitions.csv": "Wallets that changed size",
        "rank_groups.csv": "Top 10, next 90, next 900", "pools_summary.csv": "Reddex pools, start and end",
        "pools_daily.csv": "Pools and WRBNT, daily", "stake_size_bands.csv": "Stakers by stake size",
        "unlock_schedule_365.csv": "365 day pool unlocks", "named_balances.csv": "Named wallet balances",
        "named_counterparties.csv": "Named wallet counterparties", "reserved_daily.csv": "Reserved wallets, daily",
        "reserved_wrbnt.csv": "Reserved wallets, WRBNT moves", "group_flows.csv": "Flows between groups"}
    blocks += [
        ("chapter", "08", "Download the data", "files", "Data"),
        ("text", "Every chart and table above is drawn from these files. They hold groups and named wallets only."),
        ("files", [("Report as PDF", "pdf", f"downloads/rbnt-holders-{slug}.pdf"),
                   ("Report as Word", "docx", f"downloads/rbnt-holders-{slug}.docx"),
                   ("Every table in one workbook", "xlsx", f"downloads/rbnt-holders-{slug}-tables.xlsx"),
                   ("Headline figures and checks", "json", f"{data_path}/headline.json"),
                   ("Second read from the node", "json", f"{data_path}/audit.json"),
                   ("Community summary", "md", "community/summary.md")]
         + [(titles_.get(f, f), "csv", f"{data_path}/{f}") for f in H["tables"]]),
        ("chapter", "09", "Glossary", "glossary", "Glossary"),
        ("glossary", [
            ("RBNT", "The Redbelly network's own coin. 10 billion exist, all created at launch."),
            ("Address", "An account number on the chain; what it holds is visible to everyone."),
            ("Wallet", "An address whose owner signs with a private key; it may be a person or an organisation."),
            ("Contract", "An address that is a program and handles coins by fixed rules."),
            ("Holding", "RBNT plus WRBNT plus staked RBNT belonging to one address."),
            ("WRBNT", "The token form of RBNT. Each one is matched by an RBNT locked in the WRBNT contract."),
            ("Staking", "Depositing RBNT in a pool to earn rewards, which are paid in RBNT."),
            ("totalStake", "A pool contract's own running total of the RBNT its stakers have deposited."),
            ("Reward reserve", "RBNT in a pool beyond its totalStake, used to pay rewards."),
            ("Reserved wallets", "The nine Redbelly addresses published on the DAO treasury page, covering the team, "
                                 "investors, the reserve, ecosystem funds, governance and USYD/CSIRO."),
            ("Snapshot block", "The block that stands for a date: the newest one stamped before midnight UTC."),
            ("Gini index", "One number for how uneven holdings are, from 0 (all equal) to 1 (one holder has all)."),
            ("Wei", "The smallest unit of RBNT; 1 RBNT is 10<sup>18</sup> wei. Our checks are exact to the wei."),
        ]),
    ]

    # Number the charts in reading order and fill in [[chart]] references.
    order = [b[4] for b in blocks if b[0] == "chart"]
    number = {name: k + 1 for k, name in enumerate(order)}

    def resolve(x):
        if isinstance(x, str):
            for name, k in number.items():
                x = x.replace(f"[[{name}]]", str(k))
            return x
        if isinstance(x, tuple):
            if x and x[0] == "chart":
                return ("chart", number[x[4]]) + tuple(resolve(y) for y in x[2:])
            return tuple(resolve(y) for y in x)
        if isinstance(x, list):
            return [resolve(y) for y in x]
        return x
    blocks = [resolve(b) for b in blocks]

    meta = {"title": f"RBNT holders {ed}", "edition": ed, "pdf": f"downloads/rbnt-holders-{slug}.pdf",
            "description": f"How RBNT holders behaved in {ed}, read from the Redbelly chain: who holds the supply, how "
                           f"top-heavy it is, what the largest wallets did, staking and named wallets.",
            "footer": (f"Redbelly DAO Task Board. Figures from Redbelly mainnet blocks {B0:,} and {B1:,}, read {read_on}. "
                       "Trends only: no forecasts and no investment advice.")}
    (HOME / "index.html").write_text(site.page(blocks, top, meta))
    method_page(meta)

    downloads = HOME / "downloads"
    downloads.mkdir(exist_ok=True)
    for old in downloads.iterdir():
        old.unlink()
    outputs.print_pdf(HOME / "index.html", downloads / f"rbnt-holders-{slug}.pdf",
                      f"RBNT holders {ed} · Redbelly mainnet blocks {B0:,} to {B1:,}")
    png = HOME / "figures" / "png"
    outputs.svg_to_png(order, png)
    outputs.word(blocks, downloads / f"rbnt-holders-{slug}.docx", png, top, meta)
    outputs.workbook(downloads / f"rbnt-holders-{slug}-tables.xlsx", H["tables"], [
        [f"RBNT holders {ed}: every table behind the report"],
        ["Period", "1 July to 30 September 2026"],
        ["Opening snapshot", f"Block {B0:,}, the newest block before 1 July 2026 00:00 UTC"],
        ["Closing snapshot", f"Block {B1:,}, the newest block before 1 October 2026 00:00 UTC"],
        ["Units", "RBNT. 1 RBNT = 10^18 wei; all sums were made in wei and rounded only for display."],
        ["Holding", "RBNT + WRBNT + RBNT staked in either Reddex pool, counted with the owner and never twice."],
        ["Privacy", "Only publicly named wallets appear by name or address. All other addresses appear only in groups "
                    "of at least five."],
        ["Chain", cfg["chain"]["rpc_url"] + " (chain ID 151)"],
        ["Explorer", cfg["chain"]["explorer_api"]],
        ["Named wallets", cfg["reserved_wallets"]["source"]],
        ["Read on", read_on],
        ["Method", "docs/how-we-did-it.md, also published as how-we-did-it.html"],
    ])
    community(cfg, H, both, nl, c0, c1, res0, res1, wr0, wr1, top100, inside, outside, vest_out, B0, B1, read_on)
    print("  wrote index.html, how-we-did-it.html, PDF, Word file, workbook and community files")


def moves_table(tr):
    labels, grid = tr["labels"], tr["grid"]
    head = "".join(f'<th class="r">{escape(x)}</th>' for x in labels)
    body = []
    for i, row in enumerate(grid):
        cells = "".join(f'<td class="r{" stay" if i == j else ""}">{grouped(c) if isinstance(c, int) else escape(str(c))}</td>'
                        for j, c in enumerate(row[1:]))
        body.append(f"<tr><td>{escape(row[0])}</td>{cells}</tr>")
    return (f'<div class="grid-wrap"><table class="moves"><thead><tr><th>On 30 June \\ on 30 September</th>{head}</tr>'
            f"</thead><tbody>{''.join(body)}</tbody></table></div>")


def method_page(meta):
    import markdown
    html = markdown.markdown((HOME / "docs" / "how-we-did-it.md").read_text(), extensions=["tables", "fenced_code"])
    html = html.replace("<table>", '<div class="grid-wrap"><table>').replace("</table>", "</table></div>")
    (HOME / "how-we-did-it.html").write_text(site.doc_page(f"How we did it, {meta['title']}", html, meta))


def community(cfg, H, both, nl, c0, c1, res0, res1, wr0, wr1, top100, inside, outside, vest_out, B0, B1, read_on):
    ed = cfg["edition"]
    link = cfg.get("links", {}).get("report_url", "")
    moved_out = sum(f["out"] for fs in outside.values() for f in fs)
    summary = [
        f"# RBNT holders in {ed}: the short version",
        "",
        f"This is the first quarterly look at how RBNT holders behaved, covering 1 July to 30 September 2026. We read "
        f"every figure from the Redbelly chain, comparing block {B0:,} (end of 30 June) with block {B1:,} (end of 30 "
        f"September). We report groups, never individual holders, and we name only wallets that are already public.",
        "",
        f"**Staking {went(both['rbnt_start'], both['rbnt_end'], 'grew', 'shrank')}.** The two Reddex pools held "
        f"{words(both['rbnt_end'])} RBNT at the end of September, against {words(both['rbnt_start'])} at the end of June "
        f"({plus(both['change_pct'], percent)}), with the no lock pool accounting for the larger part. Part of every pool's balance "
        f"is a reserve for paying rewards; the full report separates it from the stakes.",
        "",
        f"**Vesting contracts paid out.** Contracts running token vesting code sent {words(vest_out)} WRBNT to wallets "
        f"during the quarter.",
        "",
        f"**The biggest wallets added.** The 100 largest unnamed wallets on 30 June held {words(top100['start'])} RBNT "
        f"(wrapped and staked included) and {words(top100['end'])} three months later. {top100['up']} grew by more than "
        f"1%, {top100['flat']} stayed within 1% and {top100['down'] + top100['emptied']} shrank.",
        "",
        f"**Still top-heavy.** {grouped(c1['wallets'])} wallets held 1 RBNT or more ({grouped(c0['wallets'])} in June). "
        f"The ten largest hold {percent(c1['top10'])} of what unnamed wallets hold.",
        "",
        f"**Reserved wallets.** Between them the nine reserved wallets went from {words(res0)} RBNT to {words(res1)}. Most of what they moved stayed inside the group; only "
        f"{' and '.join(outside)} sent coins outside it ({words(moved_out)} RBNT), mostly into WRBNT and the pools' "
        f"reward reserves.",
        "",
        f"**Wrapped RBNT.** WRBNT in circulation went from {words(wr0)} to {words(wr1)}, backed one to one throughout.",
        "",
        "The chain shows coins moving, not who moved them or why. Nothing here is a forecast or advice.",
        "",
        f"Full report, method and data: {link}" if link else "The full report, its method and every data file are "
                                                             "published alongside this summary.",
    ]
    (HOME / "community" / "summary.md").write_text("\n".join(summary) + "\n")

    posts = [
        f"RBNT holders, {ed}: the first quarterly on-chain holder report, read block by block from the Redbelly chain. "
        f"Groups only, no individual wallets, no price talk.",
        f"Staking: {words(both['rbnt_end'])} RBNT sat in the two Reddex pools on 30 Sep, from {words(both['rbnt_start'])} "
        f"on 30 Jun ({plus(both['change_pct'], percent)}). The no lock pool took most of the rise.",
        f"Holders: {grouped(c1['wallets'])} wallets held 1 RBNT or more on 30 Sep ({grouped(c0['wallets'])} in June). "
        f"The 10 largest hold {percent(c1['top10'])} of all RBNT in unnamed wallets.",
        f"The 100 biggest wallets of 30 Jun went from {words(top100['start'])} to {words(top100['end'])} RBNT, staked and "
        f"wrapped included. {top100['up']} grew, {top100['flat']} held flat, {top100['down'] + top100['emptied']} shrank.",
        f"Vesting contracts sent {words(vest_out)} WRBNT to wallets. Reserved wallets held {words(res1)} RBNT at the "
        f"end, against {words(res0)}, with most of their moves inside the group.",
        f"WRBNT in circulation went from {words(wr0)} to {words(wr1)}, always backed one to one by RBNT.",
        "Every figure points to a block on Redbelly mainnet, and the method, the tables and a second read from the "
        "node are published." + (f" Full report: {link}" if link else ""),
    ]
    total = len(posts)
    (HOME / "community" / "thread.txt").write_text(
        "\n\n".join(f"[{k}/{total}] {p}" for k, p in enumerate(posts, 1)) + "\n")
    outputs.cards(cfg, both, c1, B1, read_on)
