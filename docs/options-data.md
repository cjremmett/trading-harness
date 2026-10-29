# Options data

Historical end-of-day option chains loaded by `ThetaDataOptionDataWorkflow` and `ThetaDataOptionBackfillWorkflow` in `~/finance-tools`. The daily job stores the latest trading session. The backfill stores earlier sessions in a window of one calendar year before that latest session, skipping weekends and full-market holidays. Both jobs write the same table. A symbol is included when it appears in both the latest stock-symbol snapshot and the latest option-underlying snapshot.

## Table

Query this name:

```text
securities_data.securities.option_data
```

Iceberg catalog: warehouse `securities_data` at `http://192.168.0.20:8181/catalog`, namespace `securities`, table `option_data`.

Storage root of the Iceberg table:

```text
s3://securities-data/iceberg/01a17ffa-2454-7133-b1d6-bd20972d1c49
```

DuckDB reads the current snapshot through the query name. The table is not partitioned. Filter on `date`, and on `symbol` when the underlying is known. On 2026-10-29 the table held 92,443,500 rows for sessions from 2025-10-27 through 2026-10-28.

Grain is one row per underlying, expiration, strike, right, and session date. Strike is rounded to 4 decimal places when the row is loaded. `right` is the lowercase word `call` or `put`. Quote it as `"right"`; DuckDB reserves that word.

`date` is the trading session the chain belongs to (the session ThetaData's calendar selected). The symbol-list `date` further down is the America/New_York calendar day the snapshot job ran, which can be the next morning.

## Schema

| Column | DuckDB type | Meaning |
| --- | --- | --- |
| `symbol` | `VARCHAR` | Underlying ticker. |
| `expiration` | `DATE` | Option expiration. |
| `strike` | `DOUBLE` | Strike, rounded to 4 decimal places at load. |
| `right` | `VARCHAR` | `call` or `put`. |
| `created` | `TIMESTAMP` | Quote time stored as UTC with the time zone removed. Null when ThetaData omits it. Microsecond precision. |
| `last_trade` | `TIMESTAMP` | Last trade time, same UTC-naive representation as `created`. Null when omitted. |
| `open` | `DOUBLE` | Session open premium. |
| `high` | `DOUBLE` | Session high premium. |
| `low` | `DOUBLE` | Session low premium. |
| `close` | `DOUBLE` | Session close premium. |
| `volume` | `BIGINT` | Contracts traded. `0` when the source value is missing. |
| `count` | `BIGINT` | Number of trades. Null when ThetaData omits it. |
| `bid_size` | `BIGINT` | Bid size. Null when omitted. |
| `bid_exchange` | `INTEGER` | ThetaData bid exchange code. Null when omitted. |
| `bid` | `DOUBLE` | Bid. Null when omitted. |
| `bid_condition` | `INTEGER` | ThetaData bid condition code. Null when omitted. |
| `ask_size` | `BIGINT` | Ask size. Null when omitted. |
| `ask_exchange` | `INTEGER` | ThetaData ask exchange code. Null when omitted. |
| `ask` | `DOUBLE` | Ask. Null when omitted. |
| `ask_condition` | `INTEGER` | ThetaData ask condition code. Null when omitted. |
| `open_interest` | `BIGINT` | Open interest. `0` when ThetaData reports zero or sends no print for a stored contract. |
| `date` | `DATE` | Trading session. |

A symbol with an empty chain contributes no rows for that session. Absence of a symbol on a date is not the same fact as `open_interest = 0`.

```bash
uv run --no-project --with duckdb scripts/duckdb_query.py \
  "SELECT symbol, expiration, strike, \"right\", close, volume, open_interest FROM securities_data.securities.option_data WHERE symbol = 'AAPL' AND date = DATE '2026-10-27' AND \"right\" = 'call' LIMIT 20"
```

## Per-symbol volume

The same jobs write one rollup row per underlying per session. `total_volume` is the sum of contract `volume`.

Query name: `securities_data.securities.option_symbol_volume`

Storage root: `s3://securities-data/iceberg/01a17ffa-246b-7c21-b78b-c99693114dbb`

| Column | DuckDB type | Meaning |
| --- | --- | --- |
| `symbol` | `VARCHAR` | Underlying ticker. |
| `date` | `DATE` | Trading session. Same clock as `option_data.date`. |
| `total_volume` | `BIGINT` | Sum of `option_data.volume` for that symbol and session. |

## Underlying list

`ThetaDataSecuritiesWorkflow` stores ThetaData's option-underlying list: one row per symbol per America/New_York calendar day the job ran. That `date` is the snapshot's calendar day, so it can fall on the morning after `option_data.date`. Join to the chain on `symbol`.

Query name: `securities_data.securities.option_underlyings`

Storage root: `s3://securities-data/iceberg/01a17d48-023e-7940-8260-78fdaea47ed0`

| Column | DuckDB type | Meaning |
| --- | --- | --- |
| `symbol` | `VARCHAR` | Underlying ticker returned by ThetaData for that snapshot. |
| `date` | `DATE` | America/New_York calendar day of the snapshot. |
