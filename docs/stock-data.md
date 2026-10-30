# Stock data

Daily US stock and ETF bars loaded by `MarketParquetStockDataWorkflow` in `~/finance-tools`. The source files are MarketParquet `stock_daily` and `etf_daily`. Each session is appended once.

## Table

Query this name:

```text
securities_data.securities.stock_data
```

Iceberg catalog: warehouse `securities_data` at `http://192.168.0.20:8181/catalog`, namespace `securities`, table `stock_data`.

Storage root of the Iceberg table:

```text
s3://securities-data/iceberg/01a184f4-117f-76f0-b4e1-d1ca1ef75466
```

DuckDB reads the current snapshot through the query name above. The loader's staging CSVs, which are not the table to scan, are `s3://securities-data/securities/stock_data/stocks-YYYY-MM-DD.csv` and `s3://securities-data/securities/stock_data/etfs-YYYY-MM-DD.csv`.

The table is not partitioned. A `date` predicate is what keeps a scan small.

## Schema

| Column | DuckDB type | Meaning |
| --- | --- | --- |
| `date` | `DATE` | Trading session of the bar. |
| `symbol` | `VARCHAR` | Ticker. |
| `asset_type` | `VARCHAR` | `Stock` or `ETF`. |
| `open` | `DOUBLE` | Session open. |
| `high` | `DOUBLE` | Session high. |
| `low` | `DOUBLE` | Session low. |
| `close` | `DOUBLE` | Session close. |
| `volume` | `DOUBLE` | Share volume. Stored as a float because split-adjusted volume is fractional. |

Grain is one row per (`date`, `asset_type`, `symbol`). The loader rejects a session file that contains a null, a duplicate symbol, or a row for another date. `asset_type` is the whole word `Stock` or `ETF`, matching that capitalization.

`date` is the session the bar describes. It is a different clock from the symbol-list `date` in the next section.

On 2026-10-29 the table held sessions from 2025-10-28 through 2026-10-28. Confirm the edges before relying on that window:

```bash
uv run --no-project --with duckdb scripts/duckdb_query.py \
  "SELECT min(date), max(date), count(*) FROM securities_data.securities.stock_data"
```

```bash
uv run --no-project --with duckdb scripts/duckdb_query.py \
  "SELECT date, close, volume FROM securities_data.securities.stock_data WHERE symbol = 'AAPL' AND asset_type = 'Stock' ORDER BY date"
```

## Symbol list

`ThetaDataSecuritiesWorkflow` stores ThetaData's stock symbol list: one row per symbol per America/New_York calendar day the job ran. That `date` is the snapshot's calendar day, so it can fall on the morning after the session in `stock_data`. Join the two tables on `symbol`.

Query name: `securities_data.securities.stocks`

Storage root: `s3://securities-data/iceberg/01a17d48-00bd-7c43-b56f-d0457674feab`

| Column | DuckDB type | Meaning |
| --- | --- | --- |
| `symbol` | `VARCHAR` | Ticker returned by ThetaData for that snapshot. |
| `date` | `DATE` | America/New_York calendar day of the snapshot. |