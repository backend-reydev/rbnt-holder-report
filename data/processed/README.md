# Processed data

The files behind every chart and table in the report, one folder per edition.
Each file holds named wallets or groups only. No unlabelled address appears
anywhere in this folder; `scripts/10_verify.py` checks that before release.

All amounts are in RBNT (1 RBNT = 10^18 wei, shown to 6 decimal places). Every
sum was done in wei before rounding. Snapshot blocks are listed in
`config/q3-2026.json` and in `figures.json`.

| File | Contents |
| --- | --- |
| `01_supply_check.csv` | RBNT located against the 10 billion supply, WRBNT supply and backing, each pool's balance, totalStake and reward funds, at the four main snapshots |
| `02_where_rbnt_sits.csv` | Native RBNT by the place that physically holds it |
| `03_who_holds.csv` | Holdings (RBNT + WRBNT + staked) by group: reserved wallets, wallets, contract kinds, pool reward funds |
| `04_holders_by_size.csv` | Wallets and RBNT in each holding size band |
| `05_concentration.csv` | Largest 10, 100 and 1,000 shares, wallets holding half, Gini score, median |
| `05b_lorenz_curve.csv` | Lorenz curve points for wallet holdings, start and end |
| `06_cohorts.csv` | Wallets grouped by holding on 30 June and followed to 30 September |
| `06b_band_migration.csv` | Wallets by start band and end band (cells under 5 shown as <5) |
| `06c_largest_holders.csv` | Rank groups fixed on 30 June: change, added, reduced, and how each group holds its RBNT |
| `07_staking_pools.csv` | Each pool's balance, totalStake, reward funds, stakers, stake, withdrawal and reward records |
| `07b_daily_pools_and_wrbnt.csv` | Each day: pool balances, totalStake and WRBNT supply |
| `07c_staker_sizes_end.csv` | Stakers and RBNT staked by stake size, 30 September |
| `07d_lock_calendar_365_day.csv` | RBNT staked in the 365 day pool by the month its lock ends |
| `08_named_wallets.csv` | Each named wallet: balances, RBNT in and out, fees, reconciliation gap (always 0) |
| `08b_named_wallet_flows.csv` | Each named wallet's RBNT in and out by counterparty group |
| `08c_reserved_wallets_daily.csv` | Each reserved wallet's balance every day of the quarter |
| `08d_reserved_wrbnt_flows.csv` | WRBNT wrapped, unwrapped, sent and received by reserved wallets |
| `09_group_flows.csv` | RBNT and WRBNT moved between groups during the quarter |
| `figures.json` | Every headline figure, the snapshot blocks, and the result of each exact check |
| `verification.json` | Independent re-read from the node and the publishing-rule scan |
