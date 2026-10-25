# RBNT Quarterly On-Chain Holder Report

A regular, sourced report on how RBNT holders behaved over a quarter: how
holdings are spread, accumulation and selling among the largest holders (in
groups), staking in the two Reddex pools, and flows in and out of publicly
named wallets.

First edition: **Q3 2026** (1 July to 30 September 2026).

## Ground rules

- The report is about trends, not people.
- Only publicly named wallets are named: Redbelly's reserved wallets from the
  [DAO treasury page](https://redbellydao.network/treasury/), the Wrapped RBNT
  contract, the two Reddex staking pools, and exchanges or contracts that
  carry a name tag on [Routescan](https://redbelly.routescan.io).
- Every other wallet appears only inside a group. No unlabelled address is
  ever shown, and nothing is said or implied about who owns one.
- No price predictions, no investment advice.
- Every number traces back to an on-chain call logged with its source and
  date.

## Repository layout

| Path | What it holds |
| --- | --- |
| `config/q3-2026.json` | Edition settings: dates, snapshot blocks, named wallets, holder bands |
| `src/rbnt/` | RPC and explorer clients, config loader, provenance logging |
| `scripts/` | The pipeline, one numbered step per file |
| `data/raw/` | Raw pulls and `provenance.csv`. Not committed, rebuilt by the scripts |
| `data/processed/` | Aggregated CSVs behind every chart and table |
| `report/` | Report template, charts and the rendered PDF |
| `community/` | The short community summary and X thread |
| `docs/METHOD.md` | Method and data sources, written so the next edition can repeat it |
| `brand/` | Task Board brand tokens and logos |

## Running it

```
pip install -r requirements.txt
make all            # every step for the default edition
make named          # one step
make check          # brand voice check, no em or en dashes
```

For a new edition, copy `config/q3-2026.json` to a new file, change the
period, clear `snapshot_blocks`, and run with `make all EDITION=q4-2026`.

## Status

| Step | Script | Status |
| --- | --- | --- |
| 1 | Snapshot blocks | Built, run for Q3 2026 |
| 2 | Named wallet balances | Built, run for Q3 2026 |
| 3 | Holder candidates and explorer labels | Planned |
| 4 | Candidate balances, WRBNT netting | Planned |
| 5 | Aggregated analysis | Planned |
| 6 | Charts | Planned |
| 7 | Report PDF | Planned |
