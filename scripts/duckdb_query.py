#!/usr/bin/env python3
"""Run one read-only query on the local DuckDB engine (Quack, port 9494).

The engine executes the SQL. This process only submits it and prints CSV.

Usage:
    uv run --no-project --with duckdb scripts/duckdb_query.py "SHOW DATABASES"
    uv run --no-project --with duckdb scripts/duckdb_query.py -f query.sql
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

DEFAULT_URI = "quack:127.0.0.1:9494"
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
CATALOG_URI = "http://192.168.0.20:8181/catalog"
QUERY_HEADS = frozenset(
    {
        "select",
        "with",
        "show",
        "describe",
        "desc",
        "explain",
        "summarize",
        "from",
        "table",
    }
)

# Runs on the server. getenv reads the server environment, so the token and
# Garage keys are not sent in this SQL. IF NOT EXISTS leaves an ETL-created
# secret and an existing attach in place.
SETUP_SQL = (
    """
CREATE SECRET IF NOT EXISTS garage_securities (
    TYPE s3,
    KEY_ID getenv('GARAGE_ACCESS_KEY_ID'),
    SECRET getenv('GARAGE_SECRET_ACCESS_KEY'),
    ENDPOINT regexp_replace(getenv('GARAGE_S3_ENDPOINT'), '^https?://', ''),
    REGION getenv('GARAGE_S3_REGION'),
    URL_STYLE 'path',
    USE_SSL false,
    SCOPE 's3://securities-data'
)
""".strip(),
    f"""
ATTACH IF NOT EXISTS 'securities_data' AS securities_data (
    TYPE iceberg,
    URI '{CATALOG_URI}',
    AUTHORIZATION_TYPE 'none',
    ACCESS_DELEGATION_MODE 'none'
)
""".strip(),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql", nargs="?", help="A single read-only SQL statement")
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        help="File containing one read-only SQL statement",
    )
    args = parser.parse_args()
    if (args.sql is None) == (args.file is None):
        parser.error("pass a SQL statement or -f, and only one of them")
    sql = args.sql if args.sql is not None else args.file.read_text()
    statement = _require_query(sql)

    import duckdb

    token = _load_token()
    uri = os.environ.get("QUACK_URI", DEFAULT_URI).strip() or DEFAULT_URI
    connection = duckdb.connect()
    try:
        connection.execute("INSTALL quack;")
        connection.execute("LOAD quack;")
        for setup in SETUP_SQL:
            _remote(connection, uri, token, setup)
        cursor = _remote(connection, uri, token, statement)
        _write_csv(cursor)
    finally:
        connection.close()
    return 0


def _remote(connection, uri: str, token: str, sql: str):
    return connection.execute(
        "FROM quack_query(?, ?, token := ?, disable_ssl := true)",
        [uri, sql, token],
    )


def _write_csv(cursor) -> None:
    headers = [] if cursor.description is None else [col[0] for col in cursor.description]
    writer = csv.writer(sys.stdout, lineterminator="\n")
    if headers:
        writer.writerow(headers)
    while True:
        batch = cursor.fetchmany(10_000)
        if not batch:
            break
        writer.writerows(batch)


def _require_query(sql: str) -> str:
    text = _strip_leading_comments(sql).strip()
    body = text[:-1].rstrip() if text.endswith(";") else text
    if not body:
        raise SystemExit("SQL is empty")
    if ";" in body:
        raise SystemExit("pass one SQL statement")
    head = body.split(None, 1)[0].lower()
    if head not in QUERY_HEADS:
        raise SystemExit(
            "this helper runs a single read query "
            f"({', '.join(sorted(QUERY_HEADS))})"
        )
    return body


def _strip_leading_comments(sql: str) -> str:
    text = sql.strip()
    while text:
        if text.startswith("/*"):
            end = text.find("*/")
            if end < 0:
                raise SystemExit("unclosed block comment")
            text = text[end + 2 :].strip()
            continue
        if text.startswith("--"):
            newline = text.find("\n")
            text = "" if newline < 0 else text[newline + 1 :].strip()
            continue
        break
    return text


def _load_token() -> str:
    token = _env_value(ENV_FILE, "QUACK_TOKEN")
    if token:
        return token
    raise SystemExit(
        "Tell the user to put the Quack token in .env. "
        f"QUACK_TOKEN is not set in {ENV_FILE}. "
        "Copy .env.example to .env if that file does not exist, then set QUACK_TOKEN."
    )


def _env_value(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text().splitlines():
        piece = line.strip()
        if not piece or piece.startswith("#") or "=" not in piece:
            continue
        name, value = piece.split("=", 1)
        if name.strip() != key:
            continue
        token = value.strip()
        if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
            token = token[1:-1]
        return token.strip()
    return ""


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from None
