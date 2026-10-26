"""Draw every chart from the published tables into figures/*.svg."""

import csv
import json

from .. import drawing as V
from .. import edition

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def table(name):
    with open(edition.out_dir() / name) as fh:
        return list(csv.DictReader(fh))


def run(flags):
    out = edition.HOME / "figures"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.svg"):
        old.unlink()
    head = json.loads((edition.out_dir() / "headline.json").read_text())
    titles = [m["title"] for m in head["moments"].values()]
    t0, t1 = titles[0], titles[-1]

    def save(name, svg):
        (out / f"{name}.svg").write_text(svg)

    groups = {r["group"]: r for r in table("holdings_by_group.csv")}
    big = ["Redbelly reserved wallets", "Unnamed wallets", "Token vesting contracts", "Shared-key wallets (Safe)"]
    parts = [("Reserved wallets", V.INK, "on-fill"), ("Unnamed wallets", V.RED, "on-fill"),
             ("Token vesting contracts", V.SLATE, "on-fill"), ("Shared-key wallets (Safe)", V.MIST, "on-pale"),
             ("Everything else", V.PALE, "on-pale")]
    rows = []
    for t in (t0, t1):
        vals = [float(groups[g][t]) for g in big]
        rest = sum(float(r[t]) for g, r in groups.items() if g not in big)
        rows.append((t, vals + [rest]))
    save("v01_holders", V.strip(rows, parts, "Who holds the 10 billion RBNT"))

    places = {r["place"]: r for r in table("location_by_place.csv")}
    parts = [("Reserved wallets", V.INK, "on-fill"), ("WRBNT contract", V.SLATE, "on-fill"),
             ("Reddex pools", V.RED, "on-fill"), ("Other contracts", V.MIST, "on-pale"), ("Other wallets", V.PALE, "on-pale")]
    rows = []
    for t in (t0, t1):
        p = lambda k: float(places[k][t])
        rows.append((t, [p("Reserved wallets"), p("WRBNT contract (backing for WRBNT)"),
                         p("Reddex no lock pool") + p("Reddex 365 day pool"), p("All other contracts"),
                         p("All other wallets")]))
    save("v02_places", V.strip(rows, parts, "Where the coins sit, by the address that holds them"))

    bands = table("size_bands.csv")
    nw = sum(int(b[f"wallets {t1}"]) for b in bands)
    nr = sum(float(b[f"rbnt {t1}"]) for b in bands)
    fmt = lambda v: f"{v:.2f}%" if v < 1 else f"{v:.1f}%"
    save("v03_size_shares", V.dumbbell([(b["holding_rbnt"], int(b[f"wallets {t1}"]) / nw * 100,
                                         float(b[f"rbnt {t1}"]) / nr * 100) for b in bands],
                                       "Share of wallets and share of wallet RBNT, by holding size",
                                       "share of wallets", "share of RBNT", fmt=fmt, tick=lambda v: f"{v:g}%"))
    save("v04_size_change", V.diverging([(b["holding_rbnt"], int(b[f"wallets {t1}"]) - int(b[f"wallets {t0}"]))
                                         for b in bands], "Change in wallets per holding size", unit="wallets",
                                        fmt=lambda v: ("+" if v > 0 else "") + f"{v:,.0f}"))

    conc = head["concentration"]
    rows = [(t, [conc[t]["top10"], conc[t]["top100"] - conc[t]["top10"], conc[t]["top1000"] - conc[t]["top100"],
                 100 - conc[t]["top1000"]]) for t in (t0, t1)]
    save("v05_concentration", V.strip(rows, [("Top 10 wallets", V.RED, "on-fill"), ("Next 90", V.INK, "on-fill"),
                                             ("Next 900", V.SLATE, "on-fill"), ("Everyone else", V.MIST, "on-pale")],
                                      "How wallet RBNT splits by rank", unit="%"))

    co = table("cohort_outcomes.csv")
    rows = [(r["holding_on_30_june"], [int(r["up_more_than_1pct"]), int(r["flat_within_1pct"]),
                                       int(r["down_more_than_1pct"]), int(r["fell_below_1_rbnt"])])
            for r in co if r["up_more_than_1pct"]]
    save("v06_outcomes", V.strip(rows, [("Up more than 1%", V.RED, "on-fill"), ("Flat, within 1%", V.MIST, "on-pale"),
                                        ("Down more than 1%", V.SLATE, "on-fill"), ("Fell under 1 RBNT", V.INK, "on-fill")],
                                 "Outcome for each wallet, grouped by its holding on 30 June", unit="wallets"))
    save("v07_cohort_net", V.diverging([(r["holding_on_30_june"], float(r["net"])) for r in co],
                                       "Net change in RBNT for each group"))

    ranks = table("rank_groups.csv")[:3]
    rows = []
    for r in ranks:
        rows.append((f"{r['group_ranked_on_30_june']}, {t0[:6]}",
                     [float(r["in_wallet_start"]), float(r["wrapped_start"]), float(r["staked_start"])]))
        rows.append((f"{r['group_ranked_on_30_june']}, {t1[:6]}",
                     [float(r["in_wallet_end"]), float(r["wrapped_end"]), float(r["staked_end"])]))
    save("v08_rank_mix", V.stacked(rows, [("In the wallet", V.SLATE), ("Wrapped as WRBNT", V.MIST),
                                          ("Staked in Reddex", V.RED)], "How the largest wallets hold their RBNT"))

    days = table("pools_daily.csv")
    stamps = [d["day_starting_utc"] for d in days]
    ticks = [(k, f"{int(x[8:10])} {MONTHS[int(x[5:7]) - 1]}") for k, x in enumerate(stamps) if x.endswith("-01")]
    total = [float(d["no_lock_rbnt"]) + float(d["lock_365_rbnt"]) for d in days]
    save("v09_pools_both", V.daily(stamps, [("RBNT in both pools", total, "red")], "RBNT in the two Reddex pools, daily",
                                   ticks=ticks, h=260))
    for tag, name in (("no_lock", "No lock pool"), ("lock_365", "365 day pool")):
        save(f"v10_{tag}", V.daily(stamps, [("RBNT in the pool", [float(d[f"{tag}_rbnt"]) for d in days], "red"),
                                            ("Staked (totalStake)", [float(d[f"{tag}_total_stake"]) for d in days], "slate")],
                                   f"{name}, daily", ticks=ticks, shade_between=(0, 1)))

    sched = [r for r in table("unlock_schedule_365.csv") if r["unlock_month_utc"][:1].isdigit()]
    save("v12_unlocks", V.columns([f"{MONTHS[int(r['unlock_month_utc'][5:]) - 1]} {r['unlock_month_utc'][2:4]}" for r in sched],
                                  [float(r["rbnt"]) for r in sched], "Monthly unlocks in the 365 day pool"))

    named = [r for r in table("named_balances.csv") if r["category"] == "Reserved wallet"]
    save("v13_reserved_change", V.diverging([(r["name"], float(r["change"])) for r in named],
                                            "Change in each reserved wallet over the quarter"))
    reserved = {r["name"] for r in named}
    links = sorted([(r["named_wallet"], r["counterparty"], float(r["rbnt_out"])) for r in table("named_counterparties.csv")
                    if r["named_wallet"] in reserved and float(r["rbnt_out"]) >= 1e5], key=lambda x: -x[2])
    save("v14_reserved_flows", V.flows(links, "RBNT sent by reserved wallets"))
    links = sorted([(r["from_group"], r["to_group"], float(r["together"])) for r in table("group_flows.csv")
                    if r["from_group"] != r["to_group"] and float(r["together"]) >= 1e6], key=lambda x: -x[2])
    save("v15_group_flows", V.flows(links, "RBNT and WRBNT moved between groups"))
    save("v16_wrbnt", V.daily(stamps, [("WRBNT supply", [float(d["wrbnt_supply"]) for d in days], "red")],
                              "WRBNT supply, daily", ticks=ticks, h=240))
    print(f"  drew {len(list(out.glob('*.svg')))} charts into figures/")
