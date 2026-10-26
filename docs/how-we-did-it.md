# How we did it

This page is the method behind the RBNT holder report, written so that anyone
can rerun it, check a number, or produce the next quarter. Edition 1 covers
**Q3 2026**: 1 July to 30 September 2026.

## In one paragraph

We read the Redbelly chain from its first block to the last block of
30 September, listed every address that could possibly hold RBNT, and asked the
node what each one held at fixed blocks. Wrapped and staked RBNT is credited to
the address that owns it. Unnamed addresses are only ever reported inside
groups of five or more. Before any table is written, a set of exact checks has
to hold to the wei; after the tables are written, a separate stage reads the
published figures back from the node.

## What the brief asks, and where we answer it

| The brief asks for | What we measure | Tables in `data/q3-2026/` |
| --- | --- | --- |
| How holdings are spread, and how that changed | Wallets and RBNT per holding size at four dates; share of the largest 10, 100, 1,000 and 1% of wallets; fewest wallets holding over half; Gini index; Lorenz curve | `size_bands`, `concentration_measures`, `lorenz_points` |
| Accumulation and selling by the largest holders, in groups | Wallets grouped by holding on 30 June and followed to 30 September (up, flat, down, emptied, net change); top 10, next 90 and next 900 by rank; how each rank group holds its RBNT; size changes in a transition table | `cohort_outcomes`, `rank_groups`, `band_transitions` |
| Staking in the two Reddex pools | Each pool's RBNT at the start and end (the headline), split into staked RBNT and reward reserve; daily balances; stakers joining and leaving; stake, withdrawal and claim events; stake sizes; when locked stakes come free | `pools_summary`, `pools_daily`, `stake_size_bands`, `unlock_schedule_365` |
| Flows in and out of the named wallets | Each reserved wallet's balance at both dates and every day; every transfer of the quarter grouped by counterparty; WRBNT wrapped and passed on; reconciliation to the wei | `named_balances`, `named_counterparties`, `reserved_daily`, `reserved_wrbnt` |
| Labelled exchange wallets | Public name tags on the explorer | chapter 06 of the report |
| Where the supply is | All 10 billion RBNT by kind of owner and by holding address; flows between groups; coverage of the supply | `holdings_by_group`, `location_by_place`, `group_flows`, `supply_reconciliation` |

## Dates and blocks

A date in this report means the end of that day in UTC, and it is stood for by
the newest block whose timestamp is earlier than midnight. We find that block
by bisecting on block timestamps from the node, confirm that the next block is
stamped at or after midnight, and compare our answer with the explorer's
`getblocknobytime`. (The explorer counts a block stamped exactly at midnight as
"before"; we do not. That is the only difference we allow.)

| Date | Block | Stamped (UTC) |
| --- | --- | --- |
| End of 30 June 2026 (opening) | 3,025,809 | 2026-06-30 23:57:19 |
| End of 31 July 2026 | 3,104,242 | 2026-07-31 23:58:45 |
| End of 31 August 2026 | 3,161,410 | 2026-08-31 23:57:49 |
| End of 30 September 2026 (closing) | 3,209,414 | 2026-09-30 23:57:35 |

The same rule gives a block for every day of the quarter (93 in all) and for
every seventh day. Those are used for the pools, WRBNT and the reserved wallets.

## Who we name

Twelve addresses may appear by name and address, and no others.

Nine come from the DAO treasury page:

| # | Treasury page name | Address |
| --- | --- | --- |
| 1 | Team (Locked) | `0xbCee2DEfb7cF136480e3619Cf93E8129059977aF` |
| 2 | Governance (Locked) | `0x9a83957d3399CBBCbEf2112797B4a5B8e58C63d4` |
| 3 | Governance (Unlocked) | `0x9E678318539D7C98057e9F89c58fb8f99752FaeA` |
| 4 | USYD/CSIRO (Locked) | `0xAC27381EF74457c1258d54a808C2461eEdc56270` |
| 5 | Investors | `0xeF816D556E01BC194AE302999930EAcD6dc4e566` |
| 6 | Reserve | `0x7473fEAf836b5319D9190d8367991Dc6ef33C16d` |
| 7 | Ecosystem (Locked) | `0xC5c131572d232512973e79204B93C2c1D57c879D` |
| 8 | Ecosystem 2 (Unlocked) | `0xE0c701c40166BBD8D5f5Ec33c123F0A03E902DF7` |
| 9 | Ecosystem (Unlocked) | `0x415cAD8Fc89F75a63C5B830E06460EEcdE083C9F` |

Three come from the task brief:

| # | Contract | Address |
| --- | --- | --- |
| 10 | WRBNT, also tagged "Wrapped RBNT" by Routescan | `0x6ed1f491e2d31536d6561f6bdb2adc8f092a6076` |
| 11 | Reddex pool without a lock | `0x43A1dc107BBb06dF266278056055AE7Fc5bd2817` |
| 12 | Reddex pool with a 365 day lock | `0x5E8040e85D0E6363D798a43BEa939C026449946d` |

The reserved wallets come from the table the treasury page loads in its own
script. That table gives each wallet's starting allocation, which is not what
it holds today, so we use it only for names and addresses. Any address the
explorer tags with an exchange's name would be added automatically; in this
edition the explorer tagged none.

## How a holding is counted

An address's **holding** is its RBNT, plus its WRBNT balance, plus whatever it
has staked in either pool (`userInfo(address).amount`). Because of this,
wrapping or staking never looks like selling.

To count every coin exactly once:

* RBNT held by the WRBNT contract backs WRBNT one to one, so it is credited to
  the WRBNT holders and not to the contract. If the contract ever held more RBNT
  than the WRBNT supply, the excess would be shown on its own; in this edition
  there was none.
* RBNT staked in a pool is credited to the staker. What is left in the pool
  above its `totalStake` is the pool's **reward reserve**, shown separately.

Holder counts, size bands and concentration cover **unnamed wallets** holding
at least 1 RBNT. Named wallets and contracts are shown elsewhere, because the
reserved wallets are large by design and a single contract can hold coins for
many people. A wallet is an address without code at the closing block (an
address carrying only an EIP-7702 delegation marker still counts as a wallet);
anything with code is a contract.

## How we found every address

1. **Every block.** For each block from 0 to 3,209,414 we read the receipts
   (`eth_getBlockReceipts`) and the header. Receipts give us every sender,
   receiver and newly deployed contract, plus every event emitted by WRBNT or
   either pool. Headers give us the 20-byte values listed in `extraData`, which
   is where Redbelly names its governors.
2. **Every internal transfer.** Contracts also move RBNT inside other
   transactions, and the public node has no trace interface, so we read the
   explorer's `txlistinternal` by block range from block 0. Whenever a range
   comes back at the 10,000 row limit we split it, so nothing is cut off.
3. **Public tags.** We read the explorer's address list, largest first, and the
   WRBNT holder list, only to pick up public names and make sure no WRBNT
   holder is missed.

This gave 761,594 addresses. Governors matter because Redbelly pays fees to
them as plain balance changes with no transaction attached, which is also why
we never rebuild balances by adding up transfers.

## How we read balances

* RBNT of every address at the opening and closing blocks (`eth_getBalance`).
* RBNT at both month ends for every address that was non-empty at either end
  or took part in any transfer during the quarter. Any other address held
  nothing at either end and never moved, so it held nothing in between.
* WRBNT `balanceOf` at all four dates for every address that ever appeared in a
  WRBNT event or the explorer's holder list, and the WRBNT `totalSupply`.
* `userInfo` in both pools at all four dates for every address that ever
  appeared in a pool event; each pool's `totalStake` and balance at every
  daily block.
* `getStakeUnlockTimes` at the closing block for every open stake.
* `eth_getCode` at the closing block for every address that held anything.

Balances in the explorer's lists are never used: they are today's figures and
rounded.

## How we sort contracts

For every contract that held at least 1 RBNT at one of the four dates we read
the contract name from its verified source on the explorer (for a proxy, the
name of the contract behind it). That name says what the program is, never who
runs it. Names are matched in this order:

| Name contains | Kind |
| --- | --- |
| `vest` | Token vesting contracts |
| `safe`, `multisig`, `gnosis` | Shared-key wallets (Safe) |
| `bridge`, `oft`, `portal`, `gateway`, `teleport` | Cross-chain bridge contracts |
| `pair`, `pool`, `swap`, `router`, `amm`, `algebra`, `liquidity` | Exchange liquidity pools |
| `stak`, `farm`, `reward` | Other staking programs |
| no verified source | Contracts with no published code |
| anything else | Remaining contracts |

A kind with fewer than five contracts is shown as part of Remaining contracts.

## Staking: stakes and reward reserve

Both pools run the verified contract `ReddexRBNTLockStaker`. A stake adds the
RBNT sent to the staker's `userInfo.amount` and to the pool's `totalStake`; a
withdrawal takes it off both and sends it back; rewards are paid in RBNT from
the pool's own balance. A pool's RBNT balance is therefore the stakes plus a
reserve for rewards. As the brief asks, the headline figure is the pool's RBNT
balance at each date; next to it we show `totalStake` and the difference.

Stakes and withdrawals in the quarter are counted from the pools' own `Stake`
and `Unstake` events, reward claims from `ClaimLiquidXReward`. A transfer into a
pool that is not a call to `stake()` is a top-up of the reward reserve.

## Named wallet flows

For each named wallet we take every successful transaction and every internal
transfer with value between the two closing blocks, and group the other side by
who they are: another named wallet by name, a contract by its kind, or
otherwise "unnamed wallets". Fees are what the wallet paid for the transactions
it sent. WRBNT moves of the reserved wallets are read from WRBNT `Transfer`,
`Deposit` and `Withdrawal` events and listed separately, since moving a token
does not change an RBNT balance.

## Privacy safeguards

* Only the addresses in the tables above are ever shown.
* An unnamed address can contribute to a count or a total, but only inside a
  group that has five or more members. Size
  bands, stake sizes, contract kinds and unlock months are merged, or shown as
  "<5", wherever a group would be smaller.
* Contract kinds come from the program's own published name. We never guess
  who is behind an address and never add a label the explorer does not show.
* The per-address cache lives in `cache/` and is never committed. The audit
  stage and the unit tests both fail if any other address appears in a
  published file.

## The exact checks

These must all hold, in wei, before any table is written (58 checks in this
edition, listed with their results in `headline.json`):

* At each of the four dates, the WRBNT supply equals the sum of every WRBNT
  balance, and the WRBNT contract holds at least that much RBNT.
* At each date, each pool's stakers add up to its `totalStake`, and the pool's
  balance covers its `totalStake`.
* Over the quarter, for each pool, RBNT in `Stake` events minus RBNT in
  `Unstake` events equals the change in `totalStake`.
* The unlock schedule of the 365 day pool adds up to its closing `totalStake`.
* At each date, holdings (WRBNT and stakes credited to owners, reserves left in
  the pools) add up to the RBNT found.
* The changes of all groups net to the change in RBNT found.
* Every reported contract kind has at least five members.
* Every named wallet balances: opening RBNT + RBNT in - RBNT out - fees =
  closing RBNT, with a gap of zero wei.
* The balances found cover more than 99.99% of the supply and never exceed it.

## The second read

After the tables are written, the audit stage reads, straight from the node
and without the cache: every named wallet's balance at both dates, both pools'
`totalStake` at both dates and the WRBNT supply at both dates. It also reads
600 cached balances again, picked at random with a fixed seed, re-tests every
date's block, scans every published file against the house rules (no unnamed
address, no long dashes, no emoji, no price talk, no credit lines) and checks
every thread post fits in 280 characters. Results are in `audit.json`.

## Coverage

All 10 billion RBNT existed from the first block. The balances we found add up
to 99.99964% of the supply at the closing block. The remaining 36,485 RBNT sit
at addresses that never appear in any transaction, internal transfer, event or
header we read, such as addresses funded at launch and never touched. That
remainder moved by about 11 RBNT during the quarter.

## Sources

| Source | Address | Read for |
| --- | --- | --- |
| Redbelly mainnet RPC, chain ID 151 | `https://governors.mainnet.redbelly.network` | Blocks, receipts, headers, every balance, WRBNT and pool calls, bytecode |
| Routescan, Etherscan style API | `https://api.routescan.io/v2/network/mainnet/evm/151/etherscan/api` | Internal transfers, verified contract names, a second opinion on every snapshot block |
| Routescan address list | `https://api.routescan.io/v2/network/mainnet/evm/151/addresses` | The explorer's own name tags, and nothing else from it |
| Routescan WRBNT holders | `https://api.routescan.io/v2/network/mainnet/evm/151/erc20/0x6ed1f491e2d31536d6561f6bdb2adc8f092a6076/holders` | Making sure every WRBNT holder is read |
| Redbelly DAO treasury page | `https://redbellydao.network/treasury/` | Which nine addresses count as reserved, and what each is called |
| Reddex staking | `https://www.reddex.io/stake`, plus the pools' verified code | Which pools hold RBNT stakes, lock lengths, how rewards are paid |
| Task Board brand kit | `https://taskboard.redbellydao.network/brand` | Colours, type, logo use and voice |

The date the data was read is `read_on` in `headline.json`; the date of the
second read is `ran` in `audit.json`.

## Running it, and the next edition

Python 3.11 or newer, the packages in `requirements.txt`, and a Chromium that
Playwright can drive (set `CHROMIUM_PATH` to use a system Chromium).

```
pip install -r requirements.txt
make data      # blocks, crawl, traces, tags, holdings, programs (resumable)
make report    # tables, draw, publish, audit
make check     # offline: unit tests and the house-rules scan
```

Any single stage runs with `PYTHONPATH=src python -m rbnt <stage>`.

For Q4 2026:

1. Copy `config/q3-2026.json` to `config/q4-2026.json`. Change `edition`,
   `period` and `main_snapshots` (month ends are named `month_YYYY-MM-01`), and
   set `snapshot_blocks` back to null.
2. Look at the DAO treasury page again and update `reserved_wallets` if it has
   changed, with the date you read it.
3. Run `make data report EDITION=q4-2026`. From an empty cache this reads about
   3.4 million blocks; stretches with very busy blocks are split automatically.
4. Read the new report from start to finish. Sentences that describe a
   direction are generated from the numbers, but read them against the charts.
5. Publish only when the audit ends with no failures.

## Known gaps

* A block explorer can show that coins left an address; it cannot show who
  pressed the button or for what reason. A falling group total may
  be selling, a move between one owner's addresses, or a deposit into a
  contract.
* Addresses are not people. One person can use many addresses and one exchange
  address can hold coins for many people.
* Internal transfers come from the explorer. We test them indirectly: the named
  wallets, the WRBNT contract and both pools move coins mostly through internal
  transfers, and all of them balance to the wei.
* Public tags were read for the 20,000 largest addresses in the explorer's
  list, so a tag on a smaller address would be missed.
