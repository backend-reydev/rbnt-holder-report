# RBNT Quarterly On-Chain Holder Report

A regular, sourced report on how RBNT holders behaved over a quarter: how
holdings are spread, what the largest holders did as groups, staking in the two
Reddex pools, and RBNT moving in and out of publicly named wallets.

**First edition: Q3 2026** (1 July to 30 September 2026).

| Deliverable | Where |
| --- | --- |
| The report, web edition | `index.html` (served by Vercel at the site root) |
| The report, PDF | `downloads/rbnt-holder-report-q3-2026.pdf` |
| The report, Word | `downloads/rbnt-holder-report-q3-2026.docx` |
| Community summary and X thread | `community/summary.md`, `community/x_thread.txt`, `community/*.png` |
| Data behind every chart and table | `data/processed/q3-2026/*.csv`, `downloads/rbnt-holder-report-q3-2026-data.xlsx` |
| Every headline figure, machine readable | `data/processed/q3-2026/figures.json` |
| Method and sources | `docs/METHOD.md` |
| Independent verification results | `data/processed/q3-2026/verification.json` |

## Ground rules

- The report is about trends, not people.
- It names only wallets that are already public: Redbelly's reserved wallets
  from the [DAO treasury page](https://redbellydao.network/treasury/), the
  Wrapped RBNT contract, the two Reddex RBNT staking pools, and any exchange or
  contract that carries a name tag on [Routescan](https://redbelly.routescan.io).
- Every other address is counted only inside a group of at least five. No
  published file contains an unlabelled address, and a check stops the build if
  one ever appears.
- No price predictions, no investment advice, no calls to buy or sell.
- Every number is read from the chain at a stated block, and every published
  figure is re-read from the node by an independent check before release.

## How it works

```
01 snapshots          last block before each boundary, cross-checked with the explorer
02 scan_chain         every block from genesis: senders, recipients, created contracts,
                      WRBNT and pool logs, governor addresses in headers, quarter transactions
03 internal_transfers every internal transfer from genesis (explorer, by block range)
04 explorer_labels    public name tags from the explorer
05 balances           native RBNT, WRBNT and staked RBNT of every address at each snapshot
06 contracts          program type of every RBNT-holding contract, from its verified source
07 analyse            aggregated tables and figures.json, with exact checks in wei
08 charts             SVG charts in the brand palette
09 build              web page, PDF, Word file, workbook, community summary and cards
10 verify             re-reads figures from the node, scans every file for publishing rules
```

The per-address cache lives in `cache/` and is never committed. Running the
pipeline from an empty cache reads about 3.2 million blocks and a few hundred
thousand addresses from public endpoints.

## Running it

Python 3.11 or later. Chromium is used to print the PDF and render chart PNGs
(any Playwright install works).

```
pip install -r requirements.txt
make data        # read the chain (resumable)
make analyse     # tables, figures.json and the exact checks
make build       # charts, web page, PDF, Word, workbook, community files
make verify      # independent re-read from the node and publishing-rule scan
make check       # offline: unit tests and publishing-rule scan
```

For the next edition, see section 10 of `docs/METHOD.md`.

## Repository layout

| Path | What it holds |
| --- | --- |
| `config/q3-2026.json` | Edition settings: dates, snapshot blocks, named wallets, bands, contract kinds |
| `src/rbnt/` | RPC and explorer clients, cache, analysis functions, charts, page and exports |
| `scripts/` | The pipeline, one numbered step per file |
| `tests/` | Unit tests for the measures and the publishing rules |
| `data/processed/` | Aggregated CSVs, `figures.json`, `verification.json` |
| `report/charts/` | SVG charts used by every edition of the report |
| `community/` | Community summary, X thread and social cards |
| `downloads/` | PDF, Word and Excel editions |
| `assets/`, `brand/` | Site styles, fonts (SIL Open Font License) and the Task Board brand kit |
