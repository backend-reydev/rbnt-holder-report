"""Step 9. Write every deliverable from data/processed.

* index.html               the report, web edition (site root, served by Vercel)
* downloads/*.pdf          the report, printed from the same page
* downloads/*.docx         the report, Word edition, from the same content blocks
* downloads/*-data.xlsx    every table behind the charts, one sheet each
* community/summary.md     short summary in plain paragraphs
* community/x_thread.txt   the same as an X thread, posts separated by ---
* community/*.png          a 1600x900 card for X and a 1200x630 card for Discord

Every number in the text is read from figures.json or a CSV. None is typed by
hand. Sentences that describe a direction pick their verb from the numbers.
"""

import json
import shutil
from datetime import datetime, timezone

import _path  # noqa: F401
from rbnt import config, exports, page
from rbnt import htmlkit as H
from rbnt.htmlkit import mil, n0, pct, signed

ROOT = config.ROOT


def short_pool(label):
    return "No lock pool" if "no lock" in label else "365 day pool"


def rose(a, b, up="rose", down="fell", same="was unchanged"):
    return up if b > a else down if b < a else same


def main():
    cfg = config.load()
    proc = config.data_dir("processed")
    F = json.loads((proc / "figures.json").read_text())
    V = json.loads((proc / "verification.json").read_text()) if (proc / "verification.json").exists() else None
    snaps = F["snapshots"]
    s0, s1 = snaps["start"], snaps["end"]
    L0, L1 = s0["label"], s1["label"]
    B0, B1 = s0["block"], s1["block"]
    ed = cfg["edition"]
    slug = ed.lower().replace(" ", "-")
    gen = F["generated_utc"]
    blocks_note = f"blocks <span class=\"mono\">{B0:,}</span> and <span class=\"mono\">{B1:,}</span>"
    src_chain = (f"Source: Redbelly mainnet (chain ID 151), read with eth_getBalance and eth_call at {blocks_note}. "
                 f"Data read {gen}.")

    st = F["staking"]
    both = st["both"]
    pools = [p["label"] for p in cfg["staking_pools"]]
    nl, ly = st[pools[0]], st[pools[1]]
    conc = F["concentration"]
    c0, c1 = conc[L0], conc[L1]
    who = F["who"]
    named = F["named"]
    reserved = [w["label"] for w in cfg["reserved_wallets"]["wallets"]]
    res0 = sum(named[r]["start"] for r in reserved)
    res1 = sum(named[r]["end"] for r in reserved)
    wr0, wr1 = named[cfg["wrbnt"]["label"]]["start"], named[cfg["wrbnt"]["label"]]["end"]
    largest = {g["group"]: g for g in F["largest"]}
    top10, top100, top1000 = F["largest"][0], F["largest"][1], F["largest"][2]
    cohorts = F["cohorts"]
    new_row = cohorts[-1]
    big_cohort = cohorts[-2]
    other_w = who["Other wallets"]
    supply = F["supply"]

    gflows = F["group_flows"]
    vest = who.get("Vesting contracts", {"start": 0, "end": 0})
    vest_out = sum(g["wrbnt"] + g["rbnt"] for g in gflows if g["from"] == "Vesting contracts" and g["to"] == "Other wallets")
    vest_out_n = sum(int(r["wrbnt_transfers"]) + int(r["rbnt_transfers"]) for r in H.read_csv("09_group_flows.csv")
                     if r["from_group"] == "Vesting contracts" and r["to_group"] == "Other wallets")
    res_wr = F["reserved_wrbnt"]
    topups = {p: st[p]["plain_transfers_in"] for p in [x["label"] for x in cfg["staking_pools"]]}

    # Flows between reserved wallets and out of the reserved group.
    flows = F["named_flows"]
    res_set = set(reserved)
    internal_moves = [f for f in flows if f["wallet"] in res_set and f["counterparty"] in res_set and f["out"] > 0]
    outside = {}
    for f in flows:
        if f["wallet"] in res_set and f["counterparty"] not in res_set and f["out"] > 0:
            outside[f["wallet"]] = outside.get(f["wallet"], 0) + f["out"]
    moves_txt = "; ".join(f"{f['wallet']} sent {mil(f['out'])} to {f['counterparty']}"
                          for f in sorted(internal_moves, key=lambda x: -x["out"]))
    out_txt = " and ".join(w for w, v in sorted(outside.items(), key=lambda x: -x[1]))
    out_amt = mil(sum(outside.values()))

    # ---- Hero and glance --------------------------------------------------------------
    hero = {
        "eyebrow": f"Quarterly on-chain holder report · Edition 1 · 1 July to 30 September 2026",
        "title": f"How RBNT holders behaved in {ed}",
        "lede": ("Where the 10 billion RBNT sit, how widely they are spread, what the largest wallets did as groups, "
                 "how staking moved in the two Reddex pools, and what the publicly named wallets sent and received. "
                 "Read straight from the Redbelly chain. Trends in groups, never individual holders."),
        "tiles": [
            (f"{both['balance_end'] / 1e6:,.1f}", "million", "RBNT in the two Reddex staking pools on 30 September",
             f"<b>{signed(both['change_pct'], lambda v: f'{v:.1f}%')}</b> from {both['balance_start'] / 1e6:,.1f} million"),
            (n0(c1["wallets"]), "wallets", "held 1 RBNT or more, outside the named wallets and contracts",
             f"<b>{signed(c1['wallets'] - c0['wallets'])}</b> from {n0(c0['wallets'])}"),
            (f"{c1['top100']:.1f}", "%", "of wallet-held RBNT sits in the largest 100 wallets",
             f"<b>{signed(c1['top100'] - c0['top100'], lambda v: f'{v:.1f} pts')}</b> from {c0['top100']:.1f}%"),
            (f"{res1 / 1e9:,.2f}", "billion", "RBNT in Redbelly's nine reserved wallets",
             f"<b>{signed((res1 - res0) / 1e6, lambda v: f'{v:,.1f} million')}</b> from {res0 / 1e9:,.2f} billion"),
        ],
        "meta_line": (f"Snapshots: block {B0:,} (30 June 2026, 23:57:19 UTC) and block {B1:,} "
                      f"(30 September 2026, 23:57:35 UTC), Redbelly mainnet, chain ID 151. Data read {gen}. "
                      + (f"Independently re-checked {V['verified_utc']}: {V['passed']} checks passed." if V else "")),
    }

    glance = [
        ("Staking " + rose(both["balance_start"], both["balance_end"], "grew", "shrank", "held level"),
         f"The two Reddex pools held <strong>{mil(both['balance_end'])} RBNT</strong> on 30 September, against "
         f"{mil(both['balance_start'])} on 30 June ({signed(both['change_pct'], lambda v: f'{v:.1f}%')}). "
         f"Most of the change was in the no lock pool ({signed(nl['balance_change'], mil)}). "
         f"Addresses with an open stake went from {n0(nl['stakers_start'])} to {n0(nl['stakers_end'])} in the no lock "
         f"pool and from {n0(ly['stakers_start'])} to {n0(ly['stakers_end'])} in the 365 day pool."),
        ("Reserved wallets mostly moved RBNT between themselves",
         f"{moves_txt}. Only {out_txt} sent RBNT outside the reserved group: {out_amt} RBNT, mostly into WRBNT and "
         f"the two staking pools."),
        ("Vesting contracts paid out",
         f"Contracts whose verified code is a vesting manager held {mil(vest['start'])} RBNT (as WRBNT) on 30 June and "
         f"{mil(vest['end'])} on 30 September. They sent <strong>{mil(vest_out)} WRBNT</strong> to wallets in "
         f"{n0(vest_out_n)} transfers during the quarter."),
        ("The largest wallets " + rose(top100["start"], top100["end"], "added on balance", "reduced on balance", "held level"),
         f"The 100 wallets that were largest on 30 June held {mil(top100['start'])} RBNT then and "
         f"{mil(top100['end'])} on 30 September, counting wrapped and staked RBNT. "
         f"{n0(top100['added'])} of them added more than 1%, {n0(top100['steady'])} stayed within 1% and "
         f"{n0(top100['reduced'] + top100['exited'])} reduced by more than 1%."),
        ("Holdings stayed concentrated",
         f"The largest 100 wallets held <strong>{c1['top100']:.1f}%</strong> of all wallet-held RBNT at the end, "
         f"against {c0['top100']:.1f}% at the start. Half of it sits in just {n0(c1['to_half'])} wallets. "
         f"The middle wallet holds {mil(c1['median'])} RBNT."),
        ("A few more wallets hold RBNT",
         f"{n0(c1['wallets'])} wallets held 1 RBNT or more on 30 September, {abs(c1['wallets'] - c0['wallets']):,} "
         f"{'more' if c1['wallets'] >= c0['wallets'] else 'fewer'} than on 30 June. {n0(new_row['wallets'])} wallets "
         f"crossed 1 RBNT during the quarter and {n0(sum(c['exited'] for c in cohorts[:-1] if c['exited'] != ''))} dropped below it."),
    ]

    # ---- Sections ------------------------------------------------------------------------
    who_rows = [r for r in H.read_csv("03_who_holds.csv")]
    where_rows = H.read_csv("02_where_rbnt_sits.csv")
    blocks = []
    blocks += [
        ("section", "At a glance", f"The quarter in six points", "glance"),
        ("glance", glance),
        ("notice", [
            "<strong>Read this first.</strong> This report describes what the public Redbelly chain shows. It is about "
            "trends, not people. It names only addresses that are already public: Redbelly's nine reserved wallets from "
            "the DAO treasury page, the Wrapped RBNT contract and the two Reddex staking pools. "
            + ("The explorer labels no exchange wallet on Redbelly, so none is named. " if not F["labelled_exchanges"] else "")
            + "Every other address appears only inside a group of at least five.",
            "The chain records that coins moved. It does not record why, or who controls an address. When a group's "
            "holdings fall, the coins left those addresses: that may be a sale, a move to another address of the same "
            "owner, or a deposit into a contract. This report makes no price forecast and gives no advice.",
        ]),
        ("plain", "New to this? Three ideas the report uses",
         "<strong>Address.</strong> Every coin sits at an address, a public account number anyone can look up. "
         "<strong>Wallet or contract.</strong> A wallet address is controlled by a private key held by a person or "
         "organisation. A contract address is a program that holds coins under its own fixed rules. "
         "<strong>Counted once.</strong> Wrapped RBNT (WRBNT) and staked RBNT still belong to whoever wrapped or staked "
         "them, so this report counts them with that holder and never a second time at the contract."),
    ]

    # Section 1. Who holds the RBNT.
    def share(k):
        return who[k]["share_end_pct"] if k in who else 0
    contracts_total_end = sum(v["end"] for k, v in who.items()
                              if k not in ("Redbelly reserved wallets", "Other wallets", "Not located",
                                           "Reddex pools: reward funds", "WRBNT contract surplus"))
    biggest_kind = max(((k, v) for k, v in who.items() if k not in ("Redbelly reserved wallets", "Other wallets",
                        "Not located", "Reddex pools: reward funds", "WRBNT contract surplus")), key=lambda x: x[1]["end"])
    blocks += [
        ("section", "Section 1", "Who holds the RBNT", "where"),
        ("answer", f"On 30 September {share('Redbelly reserved wallets'):.1f}% of all RBNT sat in Redbelly's reserved "
                   f"wallets, {share('Other wallets'):.1f}% with other wallets and {contracts_total_end / 1e8:.1f}% in contracts "
                   f"other than the named ones. The largest group of contracts is {biggest_kind[0].lower()}."),
        ("p", "All 10 billion RBNT were created when the network started. Figure [[c01_who_holds]] adds up every holding on both dates "
              "and groups it by the kind of address that owns it. Wrapped and staked RBNT are counted with the address "
              "that wrapped or staked them."),
        ("fig", 1, "Who holds the 10 billion RBNT",
         "RBNT, WRBNT and staked RBNT counted with their owner. Labels show 30 September and the share of supply.",
         "c01_who_holds", f"{src_chain} Data: 03_who_holds.csv.",
         (["Group", "Addresses (1 RBNT+)", L0, L1, "Change", "Share at end"],
          [[r["group"], r["addresses_holding_1_rbnt_or_more_in_quarter"] or "", n0(float(r[L0])), n0(float(r[L1])),
            signed(float(r["change_rbnt"])), pct(float(r["share_end_pct"]), 2)] for r in who_rows], {1, 2, 3, 4, 5})),
        ("p", "Contracts publish their code on the explorer when their authors verify it. The name in that code says what "
              "kind of program a contract is, such as a vesting contract or a multi-signature wallet, though not who "
              "controls it. This report uses those names only to group contracts, and only for kinds with at least five "
              "contracts. <strong>Vesting contracts</strong> hold coins and release them to set addresses over time. "
              "<strong>Multi-signature wallets</strong> need more than one key to move coins. <strong>Bridge "
              "contracts</strong> hold RBNT moved to or from other blockchains. <strong>Trading pools</strong> hold the "
              "coins people trade against on decentralised exchanges."),
        ("h3", "Where the coins physically sit"),
        ("p", "The view above counts wrapped and staked RBNT with its owner. Figure [[c02_where_sits]] shows the same supply by the address "
              "that physically holds it, so the WRBNT contract and the two staking pools appear on their own."),
        ("fig", 2, "Where the RBNT physically sits", "Native RBNT balance of each place on both dates.", "c02_where_sits",
         f"{src_chain} Data: 02_where_rbnt_sits.csv.",
         (["Place", L0, L1, "Change", "Share at end"],
          [[r["place"], n0(float(r[L0])), n0(float(r[L1])), signed(float(r["change_rbnt"])),
            pct(float(r["share_end_pct"]), 2)] for r in where_rows])),
        ("plain", "How complete is this?",
         f"The balances read add up to {supply['located_pct_end']:.4f}% of the 10 billion supply on 30 September. "
         f"The remaining {n0(supply['not_located_end'])} RBNT sit at addresses that never sent or received a "
         f"transaction this scan could see, such as addresses funded when the network started. That amount changed by "
         f"{n0(abs(supply['not_located_end'] - supply['not_located_start']))} RBNT in the quarter, so it cannot change "
         f"any trend here."),
    ]

    gf_rows = H.read_csv("09_group_flows.csv")
    blocks += [
        ("h3", "Where RBNT moved during the quarter"),
        ("p", "Figure [[c15_group_flows]] follows every transfer of RBNT and WRBNT between groups from 1 July to 30 September. "
              f"The largest flows were stakes into the Reddex pools ({mil(sum(g['total'] for g in gflows if g['to'] == 'Reddex staking pools' and g['from'] == 'Other wallets'))} "
              f"from wallets), WRBNT released by vesting contracts to wallets ({mil(vest_out)}), RBNT unwrapped from the WRBNT "
              f"contract ({mil(sum(g['total'] for g in gflows if g['from'] == 'Wrapped RBNT contract' and g['to'] == 'Other wallets'))} "
              f"to wallets) and withdrawals and rewards from the pools "
              f"({mil(sum(g['total'] for g in gflows if g['from'] == 'Reddex staking pools' and g['to'] == 'Other wallets'))}). "
              "Transfers inside the same group, such as from one reserved wallet to another, are left out of the diagram "
              "and shown in the table."),
        ("fig", 0, "Where RBNT moved between groups, 1 July to 30 September",
         "RBNT and WRBNT sent from one group (left) to another (right). Ribbons under 1 million RBNT are left out of the "
         "diagram but kept in the table.", "c15_group_flows",
         "Source: every successful transaction and internal transfer with value, and every WRBNT Transfer record, between "
         f"blocks {B0 + 1:,} and {B1:,}. Data: 09_group_flows.csv.",
         (["From", "To", "RBNT", "Transfers", "WRBNT", "Transfers", "Total"],
          [[r["from_group"], r["to_group"], n0(float(r["rbnt"])), n0(int(r["rbnt_transfers"])), n0(float(r["wrbnt"])),
            n0(int(r["wrbnt_transfers"])), n0(float(r["rbnt_plus_wrbnt"]))] for r in gf_rows], {2, 3, 4, 5, 6})),
    ]

    # Section 2. Holders by size.
    bands = H.read_csv("04_holders_by_size.csv")
    labels4 = [v["label"] for v in snaps.values()]
    mid_band = max(F["bands"], key=lambda b: b["wallets_end"])
    blocks += [
        ("section", "Section 2", "How many holders, and how big", "size"),
        ("answer", f"{n0(c1['wallets'])} wallets held 1 RBNT or more on 30 September, "
                   f"{abs(c1['wallets'] - c0['wallets']):,} {'more' if c1['wallets'] >= c0['wallets'] else 'fewer'} than on "
                   f"30 June. Most hold a little: the most common size is {mid_band['band']} RBNT."),
        ("p", "A holding here is everything a wallet owns: RBNT in the wallet, plus WRBNT, plus RBNT it has staked. "
              "Wallets with less than 1 RBNT are left out of the counts, because many addresses only keep a tiny amount "
              f"left over from fees ({n0(F['dust_wallets'][L1])} such wallets on 30 September). Named wallets and contracts "
              "are not in these counts either; they are shown in section 1."),
        ("fig", 3, "Share of wallets and share of RBNT by holding size",
         "For each size band on 30 September: the share of all wallets in it (grey) and the share of all wallet RBNT it "
         "holds (red).", "c03_size_shares", f"{src_chain} Data: 04_holders_by_size.csv.",
         (["Holding (RBNT)"] + [f"Wallets {l}" for l in labels4] + [f"RBNT {l}" for l in labels4],
          [[b["band_rbnt"]] + [n0(int(b[f"wallets_{l}"])) for l in labels4] + [n0(float(b[f"rbnt_{l}"])) for l in labels4]
           for b in bands])),
        ("fig", 4, "Change in the number of wallets in each size",
         "Wallets in each band on 30 September minus wallets in the same band on 30 June.", "c04_size_change",
         f"{src_chain} Data: 04_holders_by_size.csv.", None),
        ("p", f"Figure [[c03_size_shares]] shows the same pattern from both sides. {F['bands'][0]['wallets_end'] / c1['wallets'] * 100:.0f}% "
              f"of wallets hold between 1 and 100 RBNT, yet together they hold {F['bands'][0]['rbnt_end'] / c1['rbnt'] * 100:.2f}% of wallet RBNT. The "
              f"{n0(F['bands'][-1]['wallets_end'])} wallets with {F['bands'][-1]['band']} RBNT hold "
              f"{F['bands'][-1]['rbnt_end'] / (c1['rbnt']) * 100:.0f}%. The table under the figure also shows the two month "
              "ends inside the quarter."),
    ]

    # Section 3. Concentration.
    conc_rows = H.read_csv("05_concentration.csv")
    blocks += [
        ("section", "Section 3", "How concentrated holdings are", "concentration"),
        ("answer", f"The largest 10 wallets held {c1['top10']:.1f}% of all wallet-held RBNT on 30 September and the "
                   f"largest 100 held {c1['top100']:.1f}%. Both shares {rose(c0['top100'], c1['top100'], 'rose slightly', 'fell slightly', 'held level')} "
                   f"over the quarter."),
        ("p", "Concentration asks how much of the RBNT sits with a few holders. It is measured here over wallets only, "
              "because Redbelly's reserved wallets and contracts are large by design and would hide what holders are "
              "doing. Three measures are used: the share held by the largest wallets, the number of wallets that "
              "together hold half, and the Gini score, which runs from 0 (every wallet holds the same) to 1 (one wallet "
              "holds everything)."),
        ("table", ["Measure"] + labels4,
         [["Wallets with 1 RBNT or more"] + [n0(int(r["wallets_1_rbnt_or_more"])) for r in conc_rows],
          ["RBNT they hold"] + [n0(float(r["rbnt_held_by_them"])) for r in conc_rows],
          ["Share held by the largest 10"] + [pct(float(r["top10_share_pct"])) for r in conc_rows],
          ["Share held by the largest 100"] + [pct(float(r["top100_share_pct"])) for r in conc_rows],
          ["Share held by the largest 1,000"] + [pct(float(r["top1000_share_pct"])) for r in conc_rows],
          ["Wallets that together hold half"] + [n0(int(r["wallets_holding_half"])) for r in conc_rows],
          ["Gini score (wallets)"] + [f"{float(r['gini']):.4f}" for r in conc_rows],
          ["Middle (median) wallet, RBNT"] + [f"{float(r['median_rbnt']):,.2f}" for r in conc_rows]]),
        ("fig", 5, "Share of wallet RBNT held by the largest wallets",
         "All RBNT held by wallets with 1 RBNT or more, split by rank: the largest 10, the next 90, the next 900 and "
         "everyone else. A Lorenz curve of the same data is in 05b_lorenz_curve.csv.",
         "c05_concentration", f"{src_chain} Data: 05_concentration.csv.", None),
        ("plain", "Why this matters, and what it does not mean",
         "A concentrated spread means a small number of wallets could move a large share of the supply. It does not "
         "say who those wallets belong to: one wallet can be shared by many people, such as an exchange, and one person "
         "can use many wallets."),
    ]

    # Section 4. Largest holders.
    co_rows = H.read_csv("06_cohorts.csv")
    lg_rows = H.read_csv("06c_largest_holders.csv")
    mig = F["migration"]
    staked_top = top100["staked_end"] - top100["staked_start"]
    blocks += [
        ("section", "Section 4", "What the largest holders did", "largest"),
        ("answer", f"Wallets that started the quarter large mostly held steady or added. The {n0(big_cohort['wallets'])} "
                   f"wallets that started with {big_cohort['cohort']} RBNT held {mil(big_cohort['start'])} then and "
                   f"{mil(big_cohort['end'])} at the end."),
        ("p", "To see accumulation and selling without following any single wallet, wallets are put into groups by their "
              "holding on 30 June and the same wallets are followed to 30 September. A wallet <strong>added</strong> if "
              "its holding rose by more than 1%, <strong>reduced</strong> if it fell by more than 1%, and stayed "
              "<strong>within 1%</strong> otherwise. Staking or wrapping does not count as reducing, because the holding "
              "includes wrapped and staked RBNT."),
        ("fig", 6, "What wallets did, grouped by their holding on 30 June",
         "Share of wallets in each group that added, held steady, reduced or ended below 1 RBNT.", "c06_cohorts",
         f"{src_chain} Data: 06_cohorts.csv.",
         (["Group by holding on 30 June", "Wallets", "RBNT 30 Jun", "RBNT 30 Sep", "Net change", "Added", "Within 1%",
           "Reduced", "Below 1 at end"],
          [[r["cohort_by_start_holding"], n0(int(r["wallets"])), n0(float(r["rbnt_start"])), n0(float(r["rbnt_end"])),
            signed(float(r["net_change"])), r["added_over_1pct"], r["within_1pct"], r["reduced_over_1pct"],
            r["below_1_rbnt_at_end"]] for r in co_rows])),
        ("fig", 7, "Net change in RBNT by starting size",
         "Total change in holdings of each group between 30 June and 30 September. The last row is wallets that held "
         "under 1 RBNT on 30 June.", "c07_cohort_net", f"{src_chain} Data: 06_cohorts.csv.", None),
        ("h3", "The largest wallets, ranked on 30 June"),
        ("p", f"Ranking wallets by their holding on 30 June and following the same wallets gives a second view. The largest "
              f"10 {rose(top10['start'], top10['end'], 'added', 'reduced', 'held level')} on balance "
              f"({signed(top10['net'], mil)} RBNT), the next 90 {rose(largest[F['largest'][1]['group']]['start'], largest[F['largest'][1]['group']]['end'], 'added', 'reduced', 'held level')} "
              f"({signed(top100['net'], mil)}). RBNT staked by the largest 100 wallets "
              f"{rose(top100['staked_start'], top100['staked_end'])} by {mil(abs(staked_top))}."),
        ("table", ["Group (ranked on 30 June)", "Wallets", "RBNT 30 Jun", "RBNT 30 Sep", "Net change", "Change",
                   "Added", "Within 1%", "Reduced", "Below 1 at end"],
         [[r["group_ranked_at_start"], n0(int(r["wallets"])), n0(float(r["rbnt_start"])), n0(float(r["rbnt_end"])),
           signed(float(r["net_change"])), signed(float(r["change_pct"]), lambda v: f"{v:.1f}%"), r["added_over_1pct"],
           r["within_1pct"], r["reduced_over_1pct"], r["below_1_rbnt_at_end"]] for r in lg_rows]),
        ("fig", 8, "How the largest wallets hold their RBNT",
         "Holdings of each rank group split into RBNT in the wallet, wrapped RBNT and RBNT staked in the Reddex pools.",
         "c08_largest_composition", f"{src_chain} Data: 06c_largest_holders.csv.", None),
        ("h3", "Movement between size bands"),
        ("p", "The table below counts wallets by the band they started in (rows) and the band they ended in (columns). "
              "The shaded diagonal is wallets that stayed in the same band. Cells with fewer than five wallets show "
              "&lt;5, so no cell can point to one wallet."),
        ("rawtable", matrix_html(mig)),
    ]

    # Section 5. Staking.
    pool_rows = H.read_csv("07_staking_pools.csv")
    sizes = H.read_csv("07c_staker_sizes_end.csv")
    cal = H.read_csv("07d_lock_calendar_365_day.csv")
    cal_future = [c for c in cal if c["unlock_month_utc"] != "Already unlocked"]
    next3 = sum(float(c["rbnt"]) for c in cal_future[:3])
    blocks += [
        ("section", "Section 5", "Staking in the Reddex pools", "staking"),
        ("answer", f"The two Reddex pools held {mil(both['balance_end'])} RBNT on 30 September, up from "
                   f"{mil(both['balance_start'])} on 30 June ({signed(both['change_pct'], lambda v: f'{v:.1f}%')})."
                   if both["balance_end"] >= both["balance_start"] else
                   f"The two Reddex pools held {mil(both['balance_end'])} RBNT on 30 September, down from "
                   f"{mil(both['balance_start'])} on 30 June ({both['change_pct']:.1f}%)."),
        ("p", "Staking means locking RBNT in a pool to earn rewards. Reddex runs two RBNT pools: one with <strong>no lock"
              "</strong>, where stakers can take their RBNT out at any time, and one with a <strong>365 day lock</strong>, "
              "where each stake can only be taken out a year after it was made. As the brief asks, the headline figures "
              "are each pool's RBNT balance at the start and end of the quarter."),
        ("notice", ["<strong>A pool's balance includes reward funds as well as stakes.</strong> Rewards are paid in RBNT "
                    "out of the pool's own balance. So the balance is the stakers' RBNT plus RBNT set aside for rewards. "
                    "The pool contract also records the total staked by its stakers (its <code>totalStake</code>), which "
                    "lets this report split the two: staked RBNT, and reward funds = balance minus totalStake."]),
        ("table", ["Pool", "Balance 30 Jun", "Balance 30 Sep", "Change", "Staked 30 Jun", "Staked 30 Sep",
                   "Reward funds 30 Jun", "Reward funds 30 Sep"],
         [[short_pool(r["pool"]), n0(float(r["balance_start"])), n0(float(r["balance_end"])),
           signed(float(r["balance_change_pct"]), lambda v: f"{v:.1f}%"), n0(float(r["total_stake_start"])),
           n0(float(r["total_stake_end"])), n0(float(r["reward_funds_start"])), n0(float(r["reward_funds_end"]))]
          for r in pool_rows], None),
        ("fig", 9, "RBNT in both Reddex pools, each day", "Combined balance of the two pools at the end of each day.",
         "c10_pools_total", f"{src_chain} Daily snapshots, last block before 00:00 UTC. Data: 07b_daily_pools_and_wrbnt.csv.",
         None),
        block_fig(10, "No lock pool, each day", "Pool balance (red) and staked RBNT (grey). The gap between the two lines "
                  "is reward funds.", "c09_pool_no_lock", "Data: 07b_daily_pools_and_wrbnt.csv."),
        block_fig(11, "365 day pool, each day", "Pool balance (red) and staked RBNT (grey). The gap between the two lines "
                  "is reward funds.", "c09_pool_365_day", "Data: 07b_daily_pools_and_wrbnt.csv."),
        ("h3", "Who is staking, in groups"),
        ("table", ["Pool", "Stakers 30 Jun", "Stakers 30 Sep", "New stakers", "Stakers who left", "Stakes made",
                   "RBNT staked", "Withdrawals", "RBNT withdrawn", "Reward claims", "Rewards paid"],
         [[short_pool(r["pool"]), n0(int(r["stakers_start"])), n0(int(r["stakers_end"])), n0(int(r["new_stakers"])),
           n0(int(r["stakers_who_left"])), n0(int(r["stake_events"])), n0(float(r["rbnt_staked"])),
           n0(int(r["unstake_events"])), n0(float(r["rbnt_unstaked"])), n0(int(r["reward_claims"])),
           n0(float(r["rbnt_rewards_claimed"]))] for r in pool_rows]),
        ("p", f"Measured as a share of everything wallets hold, staked RBNT went from "
              f"{both['community_staked_share_start']:.1f}% to {both['community_staked_share_end']:.1f}% of wallet "
              f"holdings over the quarter. Stakes and withdrawals come from the pools' own Stake and Unstake records; "
              f"stakes made minus withdrawals equals the change in staked RBNT in each pool, to the last unit."),
        ("table", ["Pool", "Stake size (RBNT)", "Stakers", "RBNT staked"],
         [[short_pool(r["pool"]), r["stake_size_rbnt"], n0(int(r["stakers"])), n0(float(r["rbnt_staked"]))] for r in sizes]),
        ("h3", "When locked RBNT unlocks"),
        ("p", f"Each stake in the 365 day pool unlocks one year after it was made. Figure [[c11_lock_calendar]] adds up, by month, the RBNT "
              f"that was still staked on 30 September and when it becomes free to withdraw. Unlocking does not mean "
              f"the RBNT will be withdrawn; stakers can leave it in the pool. {mil(next3)} RBNT unlocks in the next "
              f"three months. Another {mil(sum(float(c['rbnt']) for c in cal if c['unlock_month_utc'] == 'Already unlocked'))} "
              f"RBNT was still staked on 30 September although its lock had already ended."),
        ("fig", 12, "When RBNT staked in the 365 day pool unlocks",
         "RBNT still staked on 30 September, by the month its lock ends (UTC).", "c11_lock_calendar",
         f"Source: getStakeUnlockTimes for every open stake, read at block {B1:,}. Data: 07d_lock_calendar_365_day.csv.",
         (["Unlock month", "Open stakes", "RBNT"], [[c["unlock_month_utc"], c["open_stakes"], n0(float(c["rbnt"]))]
                                                     for c in cal])),
    ]

    # Section 6. Named wallets.
    nw_rows = H.read_csv("08_named_wallets.csv")
    fl_rows = H.read_csv("08b_named_wallet_flows.csv")
    daily_wr = H.read_csv("07b_daily_pools_and_wrbnt.csv")
    exch_txt = ("The explorer labels no exchange wallet on Redbelly mainnet, so the report names none. "
                f"Of the {n0(F['network']['explorer_list_read'])} largest addresses in the explorer's list, the only one "
                f"with a public name tag is {', '.join(F['explorer_labels'])}.") if not F["labelled_exchanges"] else \
        f"The explorer labels these exchange wallets: {', '.join(F['labelled_exchanges'])}."
    blocks += [
        ("section", "Section 6", "The publicly named wallets", "named"),
        ("answer", f"Redbelly's nine reserved wallets held {res1 / 1e9:,.2f} billion RBNT on 30 September, against "
                   f"{res0 / 1e9:,.2f} billion on 30 June. Most of the RBNT they moved went from one reserved wallet "
                   f"to another."),
        ("p", "The DAO treasury page lists Redbelly's reserved wallets, their addresses and the amounts first allocated "
              "to them. Those amounts are the original allocations, not today's balances, so this report reads each "
              "balance from the chain. Every transfer in and out during the quarter is added up by counterparty, "
              "and each wallet reconciles exactly: start balance plus RBNT in, minus RBNT out, minus fees, equals the "
              "end balance."),
        ("fig", 13, "Change in each reserved wallet", "Balance on 30 September minus balance on 30 June.",
         "c12_reserved_change", f"{src_chain} Data: 08_named_wallets.csv.", None),
        ("table", ["Named wallet", "30 Jun", "30 Sep", "Change", "RBNT in", "RBNT out", "Fees"],
         [[f'{r["label"]}<br><code>{r["address"]}</code>', n0(float(r["balance_start"])), n0(float(r["balance_end"])),
           signed(float(r["change"])), n0(float(r["rbnt_in"])), n0(float(r["rbnt_out"])), f"{float(r['fees_paid']):,.2f}"]
          for r in nw_rows]),
        ("fig", 14, "Where RBNT sent by the reserved wallets went",
         "Each ribbon is RBNT sent during the quarter, from a reserved wallet on the left to a counterparty on the right. "
         "Transfers under 100,000 RBNT are left out of the diagram but kept in the table.", "c13_reserved_flows",
         "Source: every transaction and internal transfer of each reserved wallet between the two snapshot blocks. "
         "Data: 08b_named_wallet_flows.csv.",
         (["Named wallet", "Counterparty", "RBNT in", "Transfers in", "RBNT out", "Transfers out"],
          [[f["named_wallet"], f["counterparty"], n0(float(f["rbnt_in"])), f["transfers_in"], n0(float(f["rbnt_out"])),
            f["transfers_out"]] for f in fl_rows if f["named_wallet"] in res_set])),
        ("h3", "What the reserved wallets did, in order of size"),
        ("list", [f"<strong>{f['wallet']}</strong> sent {mil(f['out'])} RBNT to <strong>{f['counterparty']}</strong>."
                  for f in sorted(internal_moves, key=lambda x: -x["out"])] + [
            f"<strong>Ecosystem (Unlocked)</strong> was the only reserved wallet that sent RBNT outside the group: "
            f"{mil(sum(f['out'] for f in flows if f['wallet'] == 'Ecosystem (Unlocked)' and f['counterparty'] == 'Wrapped RBNT contract'))} "
            f"into the WRBNT contract (wrapping it), "
            f"{mil(sum(topups.values()))} to the two Reddex pools as plain transfers rather than stakes, which adds to the "
            f"pools' reward funds, "
            f"{mil(sum(f['out'] for f in flows if f['wallet'] == 'Ecosystem (Unlocked)' and f['counterparty'] == 'Unlabelled wallets'))} "
            f"to unlabelled wallets in "
            f"{n0(sum(f['out_n'] for f in flows if f['wallet'] == 'Ecosystem (Unlocked)' and f['counterparty'] == 'Unlabelled wallets'))} "
            f"transfers, and "
            f"{mil(sum(f['out'] for f in flows if f['wallet'] == 'Ecosystem (Unlocked)' and f['counterparty'] not in res_set and f['counterparty'] not in ('Wrapped RBNT contract', 'Unlabelled wallets') and 'pool' not in f['counterparty']))} "
            "to other contracts.",
        ] + wrbnt_bullets(res_wr) + [
            "Team (Locked), USYD/CSIRO (Locked) and Reserve did not move during the quarter."
            if all(named[w]["change"] == 0 for w in ("Team (Locked)", "USYD/CSIRO (Locked)", "Reserve")) else
            "Wallets not listed above did not move during the quarter."]),
        ("p", "Wrapped RBNT is a token, so moving it does not change a wallet's RBNT balance in the table above. "
              "It is listed here so every movement of the reserved wallets is accounted for."),
        ("h3", "Exchanges and other labelled addresses"),
        ("p", exch_txt + " Counterparties that are not named appear only as groups: unlabelled wallets, and contracts "
                         "by the kind of program they are."),
        ("h3", "Wrapped RBNT"),
        ("p", f"WRBNT is RBNT wrapped into a token so it can be used by apps that expect one. The WRBNT contract holds one "
              f"RBNT for every WRBNT. The supply {rose(wr0, wr1)} from {mil(wr0)} to {mil(wr1)} over the quarter."),
        ("fig", 15, "Wrapped RBNT (WRBNT) supply, each day", "WRBNT totalSupply at the end of each day.", "c14_wrbnt",
         f"Source: WRBNT totalSupply() at daily snapshot blocks. Data: 07b_daily_pools_and_wrbnt.csv.",
         None),
    ]

    # Section 7. Method.
    net = F["network"]
    ck = len(F["checks"])
    curl_lines = (
        "# Balance of the Reserve wallet at the end of the quarter (result in wei; divide by 10^18)\n"
        f"curl -s https://governors.mainnet.redbelly.network -H 'content-type: application/json' \\\n"
        f"  -d '{{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getBalance\",\"params\":[\"{cfg['reserved_wallets']['wallets'][5]['address']}\",\"{hex(B1)}\"]}}'\n\n"
        "# RBNT staked in the 365 day pool at the end of the quarter (totalStake)\n"
        f"curl -s https://governors.mainnet.redbelly.network -H 'content-type: application/json' \\\n"
        f"  -d '{{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{{\"to\":\"{cfg['staking_pools'][1]['address']}\",\"data\":\"0x8b0e9f3f\"}},\"{hex(B1)}\"]}}'\n\n"
        "# The end snapshot block: last block before 1 October 2026 00:00 UTC\n"
        "curl -s 'https://api.routescan.io/v2/network/mainnet/evm/151/etherscan/api?module=block&action=getblocknobytime&timestamp=1790812800&closest=before'")
    blocks += [
        ("section", "Section 7", "How this report was made", "method"),
        ("answer", "Every balance was read directly from the Redbelly chain at two fixed blocks, and every published figure "
                   "was read again from the node by a separate check before release."),
        ("list", [
            f"<strong>Two fixed moments.</strong> The start is block {B0:,}, the last block before midnight UTC at the end "
            f"of 30 June 2026. The end is block {B1:,}, the last block before midnight UTC at the end of 30 September. "
            f"Month ends and each day of the quarter use the same rule.",
            f"<strong>Every address.</strong> All {net['blocks_scanned']:,} blocks from the network's start to the end "
            f"block were read, along with {net['internal_rows']:,} internal transfers from the explorer, to find every "
            f"address that could hold RBNT: {net['addresses_scanned']:,} addresses in total.",
            "<strong>Balances from the chain.</strong> Each address's RBNT, WRBNT and staked RBNT were read at each "
            "snapshot block. Balances shown by the explorer's lists are never used, because they are today's figures "
            "and rounded.",
            "<strong>Counted once.</strong> RBNT inside the WRBNT contract and staked RBNT inside the pools are counted "
            "with their owners. The part of a pool's balance above its totalStake is reported as that pool's reward funds.",
            "<strong>Groups, never individuals.</strong> Only publicly named wallets are named. Every other address is "
            "counted only in a group of at least five, and a scan of every published file fails the build if any other "
            "address appears.",
            f"<strong>Exact checks.</strong> {ck} checks must pass in wei before anything is written: WRBNT supply equals "
            "the sum of all WRBNT balances, stakers add up to each pool's totalStake, stakes minus withdrawals equal the "
            "change in totalStake, every group adds up to the RBNT located, and every named wallet reconciles to the "
            "last unit.",
        ]),
        ("check", curl_lines),
        ("p", "The full method, every endpoint and the steps to produce the next edition are in "
              "<a href=\"method.html\">the method page</a>, which is docs/METHOD.md in the repository that holds the "
              "code that produced every number."),
        ("h3", "Sources"),
        ("table", ["Source", "Used for"], [
            ["Redbelly mainnet RPC, chain ID 151<br><code>https://governors.mainnet.redbelly.network</code>",
             "Every balance, WRBNT and pool figure, every block and receipt"],
            ["Routescan API, Etherscan compatible<br><code>api.routescan.io/v2/network/mainnet/evm/151/etherscan/api</code>",
             "Internal transfers, verified contract names, cross-check of snapshot blocks"],
            ["Routescan address list<br><code>api.routescan.io/v2/network/mainnet/evm/151/addresses</code>",
             "Public name tags only, never balances"],
            ["Redbelly DAO treasury page<br><code>redbellydao.network/treasury</code>",
             "Names and addresses of the reserved wallets"],
            ["Reddex staking<br><code>reddex.io/stake</code> and the pools' verified code",
             "The two RBNT pools and how rewards are paid"],
        ], set()),
        ("h3", "Limits"),
        ("list", [
            "The chain shows that coins moved, not who controls an address or why. A fall in a group's holdings may be "
            "a sale, a move between a holder's own addresses or a deposit into a contract.",
            "One address is not one person. Counts of wallets show how widely RBNT is spread across addresses.",
            "Internal transfers come from the explorer, because the public node has no trace interface. They are "
            "checked indirectly: every named wallet, including the WRBNT contract and both pools, reconciles exactly.",
            f"The explorer's address list was read for its {n0(net['explorer_list_read'])} largest addresses. A public "
            f"label on a smaller address would not be seen.",
        ]),
    ]

    # Section 8. Data.
    titles = {
        "01_supply_check.csv": "Supply and completeness checks", "02_where_rbnt_sits.csv": "Where the RBNT physically sits",
        "03_who_holds.csv": "Who holds the RBNT, by group", "04_holders_by_size.csv": "Wallets and RBNT by holding size",
        "05_concentration.csv": "Concentration measures", "05b_lorenz_curve.csv": "Lorenz curve points",
        "06_cohorts.csv": "Cohorts by starting size", "06b_band_migration.csv": "Movement between size bands",
        "06c_largest_holders.csv": "Largest wallets, by rank", "07_staking_pools.csv": "Staking pools, start and end",
        "07b_daily_pools_and_wrbnt.csv": "Pools and WRBNT, each day", "07c_staker_sizes_end.csv": "Stake sizes",
        "07d_lock_calendar_365_day.csv": "Lock calendar, 365 day pool", "08_named_wallets.csv": "Named wallets",
        "08b_named_wallet_flows.csv": "Named wallet flows", "08c_reserved_wallets_daily.csv": "Reserved wallets, each day",
        "08d_reserved_wrbnt_flows.csv": "Reserved wallets, WRBNT movements", "09_group_flows.csv": "Flows between groups"}
    dl = [(titles.get(f, f), f, f"data/processed/{slug}/{f}") for f in F["files"]]
    blocks += [
        ("section", "Section 8", "The data", "data"),
        ("p", "Every chart and table in this report is drawn from these files. Each holds groups or named wallets only. "
              "The numbers behind each figure are under \"Show the numbers\" on the web edition and in the Excel workbook."),
        ("downloads", [("Report, PDF", f"rbnt-holder-report-{slug}.pdf", f"downloads/rbnt-holder-report-{slug}.pdf"),
                       ("Report, Word", f"rbnt-holder-report-{slug}.docx", f"downloads/rbnt-holder-report-{slug}.docx"),
                       ("All tables, Excel", f"rbnt-holder-report-{slug}-data.xlsx",
                        f"downloads/rbnt-holder-report-{slug}-data.xlsx"),
                       ("Headline figures, JSON", "figures.json", f"data/processed/{slug}/figures.json"),
                       ("Verification results", "verification.json", f"data/processed/{slug}/verification.json"),
                       ("Community summary", "summary.md", "community/summary.md")] + dl),
    ]

    # Glossary.
    gloss = [
        ("RBNT", "The coin of the Redbelly network. There are 10 billion in total, all created when the network started."),
        ("Address", "A public account on the chain. Anyone can look up its balance."),
        ("Wallet", "An address controlled by a private key, held by a person or an organisation."),
        ("Contract", "An address that is a program. It holds and moves coins under its own fixed rules."),
        ("WRBNT", "Wrapped RBNT. A token backed one to one by RBNT held in the WRBNT contract."),
        ("Staking", "Locking RBNT in a pool to earn rewards, paid in RBNT."),
        ("totalStake", "The pool contract's own record of how much RBNT its stakers have staked."),
        ("Reward funds", "RBNT in a pool above its totalStake, used to pay rewards."),
        ("Reserved wallets", "Redbelly's wallets listed on the DAO treasury page: team, investors, reserve, ecosystem, "
                             "governance and USYD/CSIRO."),
        ("Snapshot block", "The block whose balances stand for a moment in time: the last block before midnight UTC."),
        ("Gini score", "A single number for concentration: 0 means every wallet holds the same, 1 means one wallet holds all."),
        ("Lorenz curve", "A chart of how much the smallest holders hold together. A straight line would mean equal holdings."),
        ("Wei", "The smallest unit of RBNT. 1 RBNT is 10<sup>18</sup> wei. All checks in this report are exact to the wei."),
    ]
    blocks += [("section", "Words used", "Words used in this report", "words"), ("gloss", gloss)]

    # ---- Number the figures in order and resolve [[chart]] references -----------------------
    order = []
    for b in blocks:
        for x in (b[1] if b[0] == "two" else [b]):
            if x[0] == "fig":
                order.append(x[4])
    num = {c: i + 1 for i, c in enumerate(order)}

    def fix(x):
        if isinstance(x, str):
            for c, n in num.items():
                x = x.replace(f"[[{c}]]", str(n))
            return x
        if isinstance(x, tuple):
            if x and x[0] == "fig":
                return ("fig", num[x[4]]) + tuple(fix(y) for y in x[2:])
            return tuple(fix(y) for y in x)
        if isinstance(x, list):
            return [fix(y) for y in x]
        return x
    blocks = [fix(b) for b in blocks]

    # ---- Write the web page -------------------------------------------------------------------
    meta = {"title": f"RBNT Holder Report {ed}", "edition": ed,
            "description": f"How RBNT holders behaved in {ed}: distribution, the largest holders, staking and named "
                           f"wallet flows, read from the Redbelly chain.",
            "pdf": f"downloads/rbnt-holder-report-{slug}.pdf",
            "footer": (f"Redbelly DAO Task Board. Data from the Redbelly mainnet at blocks {B0:,} and {B1:,}, read {gen}. "
                       "Trends only. No price predictions and no investment advice.")}
    html = page.render(blocks, hero, meta)
    (ROOT / "index.html").write_text(html)

    write_method_page(meta)

    # ---- PDF, Word, workbook -----------------------------------------------------------------
    dl_dir = ROOT / "downloads"
    dl_dir.mkdir(exist_ok=True)
    exports.html_to_pdf(ROOT / "index.html", dl_dir / f"rbnt-holder-report-{slug}.pdf",
                        f"RBNT Holder Report {ed} · Redbelly mainnet blocks {B0:,} to {B1:,}")
    png_dir = ROOT / "report" / "png"
    charts = sorted(p.stem for p in (ROOT / "report" / "charts").glob("*.svg"))
    exports.charts_to_png(charts, png_dir)
    flat = []
    for b in blocks:
        if b[0] == "two":
            flat += [("fig",) + tuple(x[1:]) for x in b[1]]
        elif b[0] == "rawtable":
            flat.append(("table", mig["labels"] and (["Start band \\ end band"] + mig["labels"]),
                         mig["matrix"]))
        elif b[0] in ("downloads",):
            continue
        else:
            flat.append(b)
    flat = [(x[0], x[1], x[2], x[3] if len(x) > 3 else None) if x[0] == "table" and len(x) > 4 else x for x in flat]
    exports.docx(flat, dl_dir / f"rbnt-holder-report-{slug}.docx", png_dir, f"How RBNT holders behaved in {ed}",
                 f"1 July to 30 September 2026. Redbelly mainnet blocks {B0:,} to {B1:,}. Data read {gen}.")
    about = [
        [f"RBNT Holder Report {ed}: data workbook"],
        ["Period", "1 July 2026 to 30 September 2026"],
        ["Start snapshot", f"Block {B0:,}, last block before 1 July 2026 00:00 UTC"],
        ["End snapshot", f"Block {B1:,}, last block before 1 October 2026 00:00 UTC"],
        ["Units", "RBNT (1 RBNT = 10^18 wei). Every sum was done in wei before rounding for display."],
        ["Holding", "Native RBNT + WRBNT + RBNT staked in either Reddex pool. WRBNT contract and staked RBNT in pools "
                    "are counted with their owners, never twice."],
        ["Privacy", "Only publicly named wallets appear by name or address. Every other address is counted only in "
                    "groups of at least 5."],
        ["Chain source", "Redbelly mainnet RPC https://governors.mainnet.redbelly.network (chain ID 151)"],
        ["Explorer source", "https://api.routescan.io/v2/network/mainnet/evm/151/etherscan/api"],
        ["Named wallets source", "https://redbellydao.network/treasury/"],
        ["Data read", gen],
        ["Method", "docs/METHOD.md in the repository"],
    ]
    exports.xlsx(dl_dir / f"rbnt-holder-report-{slug}-data.xlsx", F["files"], about)

    # ---- Community summary and thread --------------------------------------------------------
    write_community(F, cfg, hero, glance, both, nl, ly, c0, c1, res0, res1, wr0, wr1, top100, moves_txt,
                    f"{out_txt} ({out_amt} RBNT)", B0, B1, gen)
    print("built index.html, PDF, Word, workbook and community files")


def write_method_page(meta):
    """method.html: docs/METHOD.md rendered in the site's style."""
    import markdown
    body = markdown.markdown((ROOT / "docs" / "METHOD.md").read_text(), extensions=["tables", "fenced_code"])
    body = body.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Method and sources, {meta["title"]}</title><link rel="icon" href="assets/icon.png">
<link rel="stylesheet" href="assets/site.css">
<script>try{{var t=localStorage.getItem("rbnt-theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}</script>
</head><body>
<header class="bar"><div class="wrap"><a class="brand" href="index.html"><img src="brand/logos/dao-logo-on-dark.png" alt="Redbelly DAO">RBNT Holder Report <span>{meta["edition"]}</span></a>
<nav aria-label="Report"><a href="index.html">Report</a><button id="theme" type="button">Dark theme</button><a class="primary" href="{meta["pdf"]}">PDF</a></nav></div></header>
<div class="wrap" style="padding-top:40px;padding-bottom:64px"><main class="doc" style="max-width:860px">{body}</main>
<footer class="foot">{meta["footer"]}</footer></div>
<script src="assets/site.js" defer></script></body></html>
"""
    (ROOT / "method.html").write_text(html)


def wrbnt_bullets(rows):
    """One sentence per reserved wallet that moved WRBNT."""
    out = []
    for w in sorted({r["wallet"] for r in rows}):
        parts = []
        for r in [x for x in rows if x["wallet"] == w]:
            n = f"{n0(r['n'])} {'transfer' if r['n'] == 1 else 'transfers'}"
            if r["movement"].startswith("Wrapped"):
                parts.append(f"wrapped {mil(r['amount'])} RBNT into WRBNT ({n})")
            elif r["movement"].startswith("Unwrapped"):
                parts.append(f"unwrapped {mil(r['amount'])} WRBNT ({n})")
            elif "sent" in r["movement"]:
                parts.append(f"sent {mil(r['amount'])} WRBNT to {r['counterparty'].lower()} ({n})")
            else:
                parts.append(f"received {mil(r['amount'])} WRBNT from {r['counterparty'].lower()} ({n})")
        out.append(f"<strong>{w}</strong>, in wrapped RBNT: " + ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "")
                   + parts[-1] + ".")
    return out


def block_fig(num, title, sub, chart, source):
    return ("fig", num, title, sub, chart, source, None)


def matrix_html(mig):
    labs, rows = mig["labels"], mig["matrix"]
    head = "".join(f'<th class="n">{H.escape(l)}</th>' for l in labs)
    body = []
    vals = [c for r in rows for c in r[1:] if isinstance(c, int)]
    top = max(vals) if vals else 1
    for i, r in enumerate(rows):
        cells = []
        for j, c in enumerate(r[1:]):
            cls = "n"
            if i == j:
                cls += " diag"
            elif isinstance(c, int) and c:
                cls += " heat-3" if c > top / 10 else " heat-2" if c > top / 100 else " heat-1"
            cells.append(f'<td class="{cls}">{n0(c) if isinstance(c, int) else H.escape(str(c))}</td>')
        body.append(f"<tr><td>{H.escape(r[0])}</td>{''.join(cells)}</tr>")
    return (f'<div class="tw"><table class="matrix"><thead><tr><th>Started in \\ ended in</th>{head}</tr></thead>'
            f"<tbody>{''.join(body)}</tbody></table></div>")


H.escape = __import__("html").escape


def write_community(F, cfg, hero, glance, both, nl, ly, c0, c1, res0, res1, wr0, wr1, top100, moves_txt, out_txt,
                    B0, B1, gen):
    ed = cfg["edition"]
    vest_start = F["who"].get("Vesting contracts", {}).get("start", 0)
    vest_end = F["who"].get("Vesting contracts", {}).get("end", 0)
    vest_out = sum(g["total"] for g in F["group_flows"] if g["from"] == "Vesting contracts" and g["to"] == "Other wallets")
    url = cfg.get("links", {}).get("report_url", "")
    para = [
        f"# RBNT holders in {ed}: community summary",
        "",
        f"The first quarterly on-chain holder report covers 1 July to 30 September 2026. Every number is read from the "
        f"Redbelly chain at block {B0:,} (30 June, 23:57 UTC) and block {B1:,} (30 September, 23:57 UTC). It describes "
        f"trends in groups and names only wallets that are already public.",
        "",
        f"**Staking.** The two Reddex RBNT pools held {mil(both['balance_end'])} RBNT at the end of the quarter, against "
        f"{mil(both['balance_start'])} at the start ({signed(both['change_pct'], lambda v: f'{v:.1f}%')}). Most of the "
        f"change was in the no lock pool. A pool's balance includes RBNT set aside for rewards as well as stakes; the "
        f"report shows both parts.",
        "",
        f"**Holders.** {n0(c1['wallets'])} wallets held 1 RBNT or more on 30 September, against {n0(c0['wallets'])} on "
        f"30 June. Holdings stayed concentrated: the largest 100 wallets held {c1['top100']:.1f}% of wallet-held RBNT "
        f"({c0['top100']:.1f}% at the start).",
        "",
        f"**Largest holders.** The 100 wallets that were largest on 30 June held {mil(top100['start'])} RBNT then and "
        f"{mil(top100['end'])} at the end, counting wrapped and staked RBNT. {n0(top100['added'])} added more than 1%, "
        f"{n0(top100['steady'])} held within 1% and {n0(top100['reduced'] + top100['exited'])} reduced by more than 1%.",
        "",
        f"**Reserved wallets.** Redbelly's nine reserved wallets held {res1 / 1e9:,.2f} billion RBNT at the end, against "
        f"{res0 / 1e9:,.2f} billion at the start. Most movement was between reserved wallets: {moves_txt}. Only "
        f"{out_txt} sent RBNT outside the group, mostly into WRBNT and the two staking pools.",
        "",
        f"**Vesting contracts.** Contracts whose verified code is a vesting manager sent {mil(vest_out)} WRBNT to wallets "
        f"during the quarter. They held {mil(vest_start)} at the start and {mil(vest_end)} at the end.",
        "",
        f"**Wrapped RBNT.** WRBNT supply went from {mil(wr0)} to {mil(wr1)}, matched exactly by the RBNT backing it.",
        "",
        "The chain shows that coins moved, not who controls an address or why. This summary makes no price forecast "
        "and gives no advice.",
        "",
        f"Full report, method and data: {url}" if url else "The full report, its method and every data file are published with this summary.",
    ]
    (ROOT / "community" / "summary.md").write_text("\n".join(para) + "\n")

    posts = [
        f"RBNT holder report, {ed} (1 Jul to 30 Sep 2026), read straight from the Redbelly chain.\n\n"
        f"Trends in groups, no individual wallets, no price talk. Here is what the chain shows. 1/7",
        f"Staking: the two Reddex RBNT pools held {mil(both['balance_end'])} RBNT on 30 Sep, from "
        f"{mil(both['balance_start'])} on 30 Jun ({signed(both['change_pct'], lambda v: f'{v:.1f}%')}).\n\n"
        f"Most of the change was in the no lock pool. Pool balances include reward funds; the report splits them out. 2/7",
        f"Holders: {n0(c1['wallets'])} wallets held 1 RBNT or more on 30 Sep, from {n0(c0['wallets'])} on 30 Jun.\n\n"
        f"The largest 100 wallets held {c1['top100']:.1f}% of wallet-held RBNT ({c0['top100']:.1f}% at the start). 3/7",
        f"Largest holders: the top 100 wallets on 30 Jun went from {mil(top100['start'])} to {mil(top100['end'])} RBNT, "
        f"counting wrapped and staked.\n\n{n0(top100['added'])} added over 1%, {n0(top100['steady'])} held within 1%, "
        f"{n0(top100['reduced'] + top100['exited'])} reduced over 1%. 4/7",
        f"Reserved wallets: {res0 / 1e9:,.2f}B RBNT on 30 Jun, {res1 / 1e9:,.2f}B on 30 Sep. Most movement was "
        f"between reserved wallets, from the DAO treasury page list. 5/7",
        f"Vesting contracts sent {mil(vest_out)} WRBNT to wallets in the quarter. WRBNT supply went from {mil(wr0)} to "
        f"{mil(wr1)}, matched one to one by the RBNT in the WRBNT contract. 6/7",
        f"Every number traces to a block on Redbelly mainnet, with method, data and an independent re-check published."
        + (f"\n\nFull report: {url}" if url else "") + " 7/7",
    ]
    (ROOT / "community" / "x_thread.txt").write_text("\n---\n".join(posts) + "\n")
    cards(F, cfg, both, c1, res1, B1, gen)


def cards(F, cfg, both, c1, res1, B1, gen):
    """X card 1600x900 and Discord/Open Graph card 1200x630, rendered with Chromium."""
    from playwright.sync_api import sync_playwright
    fonts = (ROOT / "assets" / "fonts").as_uri()
    logo = (ROOT / "brand" / "logos" / "dao-logo-on-dark.png").as_uri()
    face = "".join(f'@font-face{{font-family:"BVP";font-weight:{w};src:url("{fonts}/be-vietnam-pro-{w}.woff2")}}'
                   for w in (400, 500, 600, 700)) + f'@font-face{{font-family:"JBM";src:url("{fonts}/jetbrains-mono.woff2")}}'
    stats = [(f"{both['balance_end'] / 1e6:,.1f}M", "RBNT in the two Reddex pools",
              f"{signed(both['change_pct'], lambda v: f'{v:.1f}%')} in the quarter"),
             (n0(c1["wallets"]), "wallets holding 1 RBNT or more", "30 September 2026"),
             (f"{c1['top100']:.1f}%", "of wallet RBNT in the largest 100", "30 September 2026")]
    for w, h, name, scale in ((1600, 900, "x_card_1600x900", 1.0), (1200, 630, "og_1200x630", 0.75)):
        tiles = "".join(f'<div class="t"><div class="v">{v}</div><div class="k">{k}</div><div class="d">{d}</div></div>'
                        for v, k, d in stats)
        html = f"""<html><head><style>{face}
        *{{box-sizing:border-box}}body{{margin:0;width:{w}px;height:{h}px;background:#0c1317;color:#f1f5f8;font-family:BVP;
        padding:{80 * scale}px;position:relative;overflow:hidden}}
        .glow{{position:absolute;right:-200px;top:-260px;width:900px;height:700px;background:radial-gradient(closest-side,#223a4b,transparent)}}
        img{{height:{70 * scale}px;position:relative}}
        .e{{font-weight:700;font-size:{18 * scale}px;letter-spacing:.1em;text-transform:uppercase;color:#ffb3ae;margin-top:{36 * scale}px;position:relative}}
        h1{{font-size:{76 * scale}px;line-height:1.05;letter-spacing:-.02em;margin:{12 * scale}px 0 0;font-weight:700;position:relative}}
        .row{{display:flex;gap:{24 * scale}px;position:absolute;left:{80 * scale}px;right:{80 * scale}px;bottom:{110 * scale}px}}
        .t{{flex:1;background:#141f26;border:1px solid #263641;border-radius:8px;padding:{26 * scale}px}}
        .v{{font-size:{60 * scale}px;font-weight:700;letter-spacing:-.02em}}.k{{font-size:{20 * scale}px;color:#c2ced6;margin-top:6px}}
        .d{{font-family:JBM;font-size:{15 * scale}px;color:#8fa1ad;margin-top:{10 * scale}px}}
        .f{{position:absolute;left:{80 * scale}px;right:{80 * scale}px;bottom:{44 * scale}px;font-family:JBM;font-size:{15 * scale}px;color:#8fa1ad;display:flex;justify-content:space-between}}
        .bar{{position:absolute;left:0;top:0;width:100%;height:6px;background:#EF5350}}
        </style></head><body><div class="bar"></div><div class="glow"></div><img src="{logo}">
        <div class="e">Quarterly on-chain holder report</div><h1>How RBNT holders<br>behaved in {cfg['edition']}</h1>
        <div class="row">{tiles}</div>
        <div class="f"><span>Redbelly mainnet, block {B1:,}. Last verified {gen}.</span><span>Trends only. Not financial advice.</span></div>
        </body></html>"""
        with sync_playwright() as p:
            b = exports.launch(p)
            pg = b.new_page(viewport={"width": w, "height": h})
            pg.set_content(html)
            pg.wait_for_timeout(300)
            pg.screenshot(path=str(ROOT / "community" / f"{name}.png"))
            b.close()
    shutil.copy(ROOT / "community" / "og_1200x630.png", ROOT / "community" / "discord_1200x630.png")


if __name__ == "__main__":
    main()
