"""Step 8. Draw every chart from the processed CSV files.

Writes SVG files to report/charts/. The same SVG is embedded in the web page,
printed into the PDF and rendered to PNG for the Word file.
"""

import csv
import json

import _path  # noqa: F401
from rbnt import config
from rbnt import svgcharts as C

OUT = config.ROOT / "report" / "charts"


def read(name):
    with open(config.data_dir("processed") / name) as f:
        return list(csv.DictReader(f))


def save(name, svg):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.svg").write_text(svg)


def main():
    for old in OUT.glob("*.svg"):
        old.unlink()
    fig = json.loads((config.data_dir("processed") / "figures.json").read_text())
    labels = [v["label"] for v in fig["snapshots"].values()]
    L0, L1 = labels[0], labels[-1]

    # 1. Who holds the RBNT (positions, counted once).
    rows = [r for r in read("03_who_holds.csv") if r["group"] != "Not located"]
    rows = [(r["group"], float(r[L0]), float(r[L1])) for r in rows if max(float(r[L0]), float(r[L1])) >= 1e6]
    save("c01_who_holds", C.hbar_pair(rows, "Who holds the 10 billion RBNT", label_w=270,
         end_note=lambda lab, s, e: f"{C.fmt_num(e)} ({e / 1e8:.1f}%)"))

    # 2. Where the coins physically sit.
    rows = [(r["place"], float(r[L0]), float(r[L1])) for r in read("02_where_rbnt_sits.csv")
            if r["place"] != "Not located"]
    save("c02_where_sits", C.hbar_pair(rows, "Where the RBNT physically sits", label_w=270))

    # 3 and 4. Holding size: share of wallets against share of RBNT, and the change in wallet counts.
    bands = read("04_holders_by_size.csv")
    nw = sum(int(b[f"wallets_{L1}"]) for b in bands)
    nr = sum(float(b[f"rbnt_{L1}"]) for b in bands)
    rows = [(b["band_rbnt"], int(b[f"wallets_{L1}"]) / nw * 100, float(b[f"rbnt_{L1}"]) / nr * 100) for b in bands]
    save("c03_size_shares", C.hbar_pair(rows, "Share of wallets and share of RBNT in each holding size, 30 September",
                                        unit="%", series=("Share of wallets", "Share of wallet RBNT"),
                                        value_fmt=lambda v, *_: f"{v:.0f}%",
                                        end_note=lambda lab, s, e: f"{s:.2f}% of wallets, {e:.1f}% of RBNT" if s < 1
                                        else f"{s:.1f}% of wallets, {e:.1f}% of RBNT"))
    save("c04_size_change", C.diverging_bars([(b["band_rbnt"], int(b[f"wallets_{L1}"]) - int(b[f"wallets_{L0}"]))
                                              for b in bands], "Change in the number of wallets in each size",
                                             unit="wallets"))

    # 5. Concentration: who holds the wallet RBNT, by rank.
    lg = read("06c_largest_holders.csv")
    conc = json.loads((config.data_dir("processed") / "figures.json").read_text())["concentration"]
    rows = []
    for lab in (L0, L1):
        c = conc[lab]
        t10, t100, t1000 = c["top10"], c["top100"] - c["top10"], c["top1000"] - c["top100"]
        rows.append((lab, c["rbnt"], [t10, t100, t1000, 100 - c["top1000"]]))
    parts = [("Largest 10", C.ACCENT, "val-in"), ("Next 90", C.DARK, "val-in"), ("Next 900", C.MUTED, "val-in"),
             ("Everyone else", C.LIGHT, "val")]
    save("c05_concentration", C.stacked_100(rows, parts, "Share of wallet RBNT held by the largest wallets",
                                            unit="%", total_fmt=lambda v: C.fmt_num(v), total_label="RBNT",
                                            label_w=120))

    # 6. Cohorts: what wallets in each starting size did.
    co = [r for r in read("06_cohorts.csv") if not r["cohort_by_start_holding"].startswith("New")]
    parts = [("Added over 1%", C.ACCENT, "val-in"), ("Within 1%", C.LIGHT, "val"),
             ("Reduced over 1%", C.MUTED, "val-in"), ("Below 1 RBNT at end", C.DARK, "val-in")]
    rows = [(r["cohort_by_start_holding"], int(r["wallets"]),
             [int(r["added_over_1pct"]), int(r["within_1pct"]), int(r["reduced_over_1pct"]),
              int(r["below_1_rbnt_at_end"])]) for r in co]
    save("c06_cohorts", C.stacked_100(rows, parts, "What wallets did, grouped by their holding on 30 June", label_w=170))

    # 7. Net change by cohort.
    allco = read("06_cohorts.csv")
    save("c07_cohort_net", C.diverging_bars([(r["cohort_by_start_holding"], float(r["net_change"])) for r in allco],
                                            "Net change in RBNT by starting size", label_w=190))

    # 8. Largest holders: composition of holdings, start and end.
    lg = read("06c_largest_holders.csv")
    rows = []
    for r in lg[:3]:
        rows.append((f"{r['group_ranked_at_start']}, {L0[:6]}", [float(r["native_start"]), float(r["wrbnt_start"]), float(r["staked_start"])]))
        rows.append((f"{r['group_ranked_at_start']}, {L1[:6]}", [float(r["native_end"]), float(r["wrbnt_end"]), float(r["staked_end"])]))
    save("c08_largest_composition", C.stacked_pair(rows, [("RBNT in the wallet", C.MUTED), ("Wrapped (WRBNT)", C.LIGHT),
                                                          ("Staked in Reddex", C.ACCENT)],
                                                   "How the largest wallets hold their RBNT", label_w=220))

    # 9 and 10. Staking pools, daily.
    daily = read("07b_daily_pools_and_wrbnt.csv")
    xs = [d["day_start_utc"] for d in daily]
    ticks = [(i, f"{x[8:10]}/{x[5:7]}") for i, x in enumerate(xs) if x.endswith("-01") or i == len(xs) - 1]
    for short, title in (("no_lock", "Reddex no lock pool"), ("365_day", "Reddex 365 day pool")):
        bal = [float(d[f"{short}_pool_balance"]) for d in daily]
        stk = [float(d[f"{short}_total_stake"]) for d in daily]
        save(f"c09_pool_{short}", C.lines_chart(xs, [("Pool balance", bal, "accent"), ("Staked RBNT (totalStake)", stk, "muted")],
                                                f"{title}: RBNT in the pool, each day", x_labels=ticks, h=280))
    tot = [float(d["no_lock_pool_balance"]) + float(d["365_day_pool_balance"]) for d in daily]
    save("c10_pools_total", C.lines_chart(xs, [("Both pools", tot, "accent")], "RBNT in both Reddex pools, each day",
                                          x_labels=ticks, h=260))

    # 11. Lock calendar of the 365 day pool.
    cal = [r for r in read("07d_lock_calendar_365_day.csv") if r["unlock_month_utc"] != "Already unlocked"]
    months = [r["unlock_month_utc"] for r in cal]
    names = [f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(m[5:]) - 1]} {m[2:4]}" for m in months]
    save("c11_lock_calendar", C.columns(names, [float(r["rbnt"]) for r in cal],
                                        "When RBNT staked in the 365 day pool unlocks", h=260))

    # 12. Reserved wallets: change in the quarter.
    nw = [r for r in read("08_named_wallets.csv") if r["category"] == "Reserved wallet"]
    save("c12_reserved_change", C.diverging_bars([(r["label"], float(r["change"])) for r in nw],
                                                 "Change in each reserved wallet, 30 June to 30 September", label_w=200))

    # 13. Reserved wallet flows.
    flows = read("08b_named_wallet_flows.csv")
    reserved = {r["label"] for r in nw}
    fl = []
    for f in flows:
        if f["named_wallet"] in reserved and float(f["rbnt_out"]) >= 1e5:
            fl.append((f["named_wallet"], f["counterparty"], float(f["rbnt_out"])))
    fl.sort(key=lambda x: -x[2])
    if fl:
        save("c13_reserved_flows", C.flow_diagram(fl, "Where RBNT sent by the reserved wallets went"))

    # 15. Group to group flows over the quarter.
    gf = [(r["from_group"], r["to_group"], float(r["rbnt_plus_wrbnt"])) for r in read("09_group_flows.csv")
          if r["from_group"] != r["to_group"] and float(r["rbnt_plus_wrbnt"]) >= 1e6]
    gf.sort(key=lambda x: -x[2])
    save("c15_group_flows", C.flow_diagram(gf, "Where RBNT moved between groups in the quarter"))

    # 14. WRBNT supply, daily.
    wr = [float(d["wrbnt_supply"]) for d in daily]
    save("c14_wrbnt", C.lines_chart(xs, [("WRBNT supply", wr, "accent")], "Wrapped RBNT (WRBNT) supply, each day",
                                    x_labels=ticks, h=240))
    print(f"wrote {len(list(OUT.glob('*.svg')))} charts to {OUT}")


if __name__ == "__main__":
    main()
