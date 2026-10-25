# Method and Data Sources

This note is written so anyone can produce the next edition and get the same
numbers for the same quarter.

## 1. Period and snapshot blocks

- Quarter: 1 July 2026 00:00 UTC to 30 September 2026 23:59:59 UTC.
- Start snapshot: the last block before 1 July 2026 00:00 UTC.
- End snapshot: the last block before 1 October 2026 00:00 UTC.
- Found with the Routescan `getblocknobytime` endpoint (`closest=before`) and
  checked against the RPC: the block's timestamp is before the boundary and
  the next block's timestamp is at or after it.

| Snapshot | Block | Block time (UTC) |
| --- | --- | --- |
| Start | 3025809 | 2026-06-30 23:57:19 |
| End | 3209414 | 2026-09-30 23:57:35 |

## 2. Data sources

| Source | Used for | Address |
| --- | --- | --- |
| Redbelly mainnet RPC, chain ID 151 | Balances at a given block (`eth_getBalance`, `eth_call`) | https://governors.mainnet.redbelly.network |
| Routescan Etherscan compatible API | Block by time, transfers, token holders | https://api.routescan.io/v2/network/mainnet/evm/151/etherscan/api |
| Routescan v2 API | Top balances list and explorer name tags | https://api.routescan.io/v2/network/mainnet/evm/151 |
| DAO treasury page | Names and addresses of the reserved wallets | https://redbellydao.network/treasury/ |
| Reddex staking page | The two RBNT staking pools | https://www.reddex.io/stake |

Every request is logged to `data/raw/<edition>/provenance.csv` with the UTC
time, the source and the exact query.

The treasury page table lists the **original allocations**, not current
balances. The report uses only the names and addresses from that table. All
balances come from the chain at the two snapshot blocks.

## 3. Named wallets

Only these are ever named:

1. Redbelly's reserved wallets on the DAO treasury page (team, investors,
   reserve, ecosystem, governance, USYD/CSIRO).
2. The Wrapped RBNT contract, `0x6ed1f491e2d31536d6561f6bdb2adc8f092a6076`.
3. The Reddex RBNT staking pools: no lock
   `0x43A1dc107BBb06dF266278056055AE7Fc5bd2817` and 365 day lock
   `0x5E8040e85D0E6363D798a43BEa939C026449946d`.
4. Exchange or contract wallets that carry a name tag on Routescan, using the
   explorer's own label text.

Every other wallet is unlabelled. Unlabelled wallets appear only as members of
a group (a balance band or a top N group). Their addresses are kept in
`data/raw`, which is not published.

## 4. Counting WRBNT once

The Wrapped RBNT contract holds RBNT one to one against the WRBNT it has
issued. To avoid counting the same tokens twice:

- The RBNT balance of the WRBNT contract is removed from the holder
  distribution.
- Each wallet's holding is native RBNT plus WRBNT, both read at the snapshot
  block.
- The WRBNT contract's balance is still shown on its own as a named wallet, so
  readers can see how much RBNT is wrapped.

## 5. Staking

Staking is read from the RBNT balances of the two Reddex pools at the start
and end snapshots. Rewards are paid in RBNT, so **a pool balance may include
reward funds as well as staked RBNT**. The change in a pool's balance is
therefore the net of new stakes, withdrawals, reward top ups and reward
payouts. It is a measure of RBNT sitting in the pool, not an exact count of
staked principal.

## 6. Holder distribution and concentration

Planned measures, all computed after the WRBNT netting in section 4:

- Number of holders above the dust threshold (1 RBNT) at each snapshot.
- Holders and RBNT held in each balance band (in RBNT: under 1,000; 1,000 to
  10,000; 10,000 to 100,000; 100,000 to 1 million; 1 million to 10 million;
  over 10 million).
- Share of circulating supply held by the top 10, 50, 100 and 500 wallets.
  This is shown with and without the named wallets, because the reserved
  wallets and contracts are large and would otherwise dominate.
- Gini coefficient as a single concentration score.

## 7. Accumulation and selling

For wallets in the top groups, compare the start and end balance. A wallet
counts as accumulating if its balance rose by more than 1 percent, selling if
it fell by more than 1 percent, and steady otherwise. Results are reported as
counts and totals per group only.

A falling balance is not always a sale. RBNT can move to a staking pool,
another wallet owned by the same holder, or a contract. Where RBNT moved into
a named staking pool or the WRBNT contract, that is noted.

## 8. Named wallet flows

For each named wallet: balance at start, balance at end, and net change.
Inflows and outflows within the quarter are summed from transfer history,
grouped by counterparty type: other named wallets, labelled exchanges,
staking pools, and unlabelled wallets (as one group).

## 9. Known limits

- Native RBNT has no holder list endpoint. The candidate holder set is built
  from the explorer's top balance list, the WRBNT holder list and transfer
  counterparties of the named wallets. Small wallets outside that set are not
  counted individually. Their combined size is checked against total supply
  and reported as a residual.
- Explorer labels can change. The labels used are the ones shown on the date
  of the pull, recorded in `provenance.csv`.

## 10. Producing the next edition

1. Copy `config/q3-2026.json` to `config/q4-2026.json` and update `edition`,
   `period` and clear `snapshot_blocks`.
2. Re-read the DAO treasury page and update `reserved_wallets` if anything
   changed. Record the date read.
3. Run `make all EDITION=q4-2026`.
4. Update the report text in `report/` and the summary in `community/`.
5. Run `make check` before publishing.
