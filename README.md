# trading-harness

This repo is the harness for agents that scan for trading signals and run trading tasks. Historical market data is loaded by the ETL in `~/finance-tools` into the `securities_data` Iceberg warehouse. Agents query that warehouse through the DuckDB engine on this machine at port 9494. The docs below are the source for table names, schemas, and the query command.

Further datasets can be added later. Document each new source under `docs/` and add it to this list.

## Data access

- [Connecting to DuckDB](docs/duckdb.md) — How to run a query on the DuckDB engine at port 9494, using `scripts/duckdb_query.py`.
- [Stock data](docs/stock-data.md) — Path and schema of the daily stock and ETF bars in `securities_data.securities.stock_data`.
- [Options data](docs/options-data.md) — Path and schema of the historical option chains in `securities_data.securities.option_data`, plus the per-symbol volume and open-interest rollups.
