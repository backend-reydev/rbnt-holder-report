# RBNT holder report

A quarterly, fully sourced look at how holders of RBNT, the Redbelly network's
coin, behaved: who holds the supply, how top-heavy it is, what the largest
wallets did as groups, how much is staked with Reddex, and what moved in and
out of the wallets with public names.

This repository holds the first edition, **Q3 2026** (1 July to 30 September
2026), and everything needed to make the next one.

## What is here

| You want | Open |
| --- | --- |
| The report on the web | `index.html`, served from the repository root |
| The report as a PDF or Word file | `downloads/` |
| The short summary and the thread | `community/summary.md`, `community/thread.txt` |
| Cards for X and Discord | `community/card-x.png` (1600x900), `community/card-discord.png` (1200x630) |
| The numbers behind every chart | `data/q3-2026/*.csv`, or the workbook in `downloads/` |
| Headline figures and the result of every check | `data/q3-2026/headline.json`, `data/q3-2026/audit.json` |
| The method | `docs/how-we-did-it.md`, also published as `how-we-did-it.html` |

## The rules the report keeps

* It describes groups and trends, never individual holders.
* It names only addresses that are already public: Redbelly's reserved wallets
  on the [DAO treasury page](https://redbellydao.network/treasury/), the
  Wrapped RBNT contract, the two Reddex RBNT pools, and anything the
  [Routescan](https://redbelly.routescan.io) explorer tags with a public name.
* An unnamed address only ever counts towards a group of five or more, and a
  scan of every published file fails if one turns up by itself.
* It forecasts nothing and advises nothing.
* Every figure is read from the chain at a stated block and read again by a
  separate stage before release.

## How it is built

One command line, `python -m rbnt <stage>`, with ten stages:

| Stage | Does |
| --- | --- |
| `blocks` | finds the block for each date and checks it against the explorer |
| `crawl` | reads every block from genesis for addresses, WRBNT and pool events, governors and quarter transactions |
| `traces` | reads every internal transfer from the explorer |
| `tags` | reads public name tags |
| `holdings` | reads RBNT, WRBNT and staked RBNT of every address at each date |
| `programs` | reads what kind of program each RBNT-holding contract is |
| `tables` | writes the published tables and `headline.json` after 58 exact checks |
| `draw` | draws the charts into `figures/` |
| `publish` | writes the web page, PDF, Word file, workbook, summary, thread and cards |
| `audit` | reads published figures again from the node and scans every file |

```
pip install -r requirements.txt
make data       # blocks to programs, resumable
make report     # tables to audit
make check      # offline unit tests and file scan
```

The per-address cache sits in `cache/` and is never committed.

## Layout

| Folder | Contents |
| --- | --- |
| `config/` | One settings file per edition: dates, named wallets, size bands, contract kinds |
| `src/rbnt/` | Node and explorer clients, the cache, measures, charts, page and exports |
| `src/rbnt/stages/` | The ten stages |
| `tests/` | Unit tests for the measures and the house rules |
| `data/q3-2026/` | Published tables, `headline.json`, `audit.json` |
| `figures/` | Charts as SVG, plus PNG copies for the Word file |
| `assets/`, `brand/` | Page style and script, fonts (SIL Open Font License), Task Board brand kit |
