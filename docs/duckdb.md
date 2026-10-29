# DuckDB

The query engine on this machine is DuckDB, served over Quack at `127.0.0.1:9494`. SQL runs on that server. The server already has the Iceberg extension and the Garage credentials, so a client only submits the statement.

Use `scripts/duckdb_query.py`. It loads `QUACK_TOKEN` from `.env` in the repo root (see `.env.example`). When that value is missing, the script tells you to ask the user to put the Quack token in `.env`. It connects to `quack:127.0.0.1:9494` with TLS disabled, attaches the `securities_data` warehouse if the server does not already have it, and prints CSV (header included) to stdout. Set `QUACK_URI` to point the script at a different engine. Pass one read query: `SELECT`, `WITH`, `SHOW`, `DESCRIBE`, `EXPLAIN`, `SUMMARIZE`, `FROM`, or `TABLE`.

```bash
uv run --no-project --with duckdb scripts/duckdb_query.py "SHOW DATABASES"
uv run --no-project --with duckdb scripts/duckdb_query.py -f query.sql
```

## Databases on the engine

| Database | Contents |
| --- | --- |
| `securities_data` | Lakekeeper warehouse `securities_data` at `http://192.168.0.20:8181/catalog`. Daily stock and ETF bars and option history. See [stock-data.md](stock-data.md) and [options-data.md](options-data.md). |
| `kweb_holdings` | Attached when the engine starts. ETF holdings live in `kweb_holdings.holdings.kweb_holdings`. Column names contain spaces and punctuation, so quote them. `DESCRIBE` that table before using it. |
| `memory` | The server's empty in-memory database. |

`securities_data` storage is the Garage bucket `s3://securities-data` (Iceberg prefix `iceberg`) at `http://192.168.0.20:3900`. Query the attached database. The script's attach uses catalog authorization `none`, which is how this warehouse is published.

Quote the option column `"right"`. DuckDB reserves that word, and a bare `right` is a syntax error. Filter `option_data` on `date` and, when the symbol is known, on `symbol`. On 2026-10-29 that table held 92,443,500 rows.
