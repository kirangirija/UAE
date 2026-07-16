"""
Validates data provenance for the curated (Tier 2) dataset:

1. Completeness — every row in every citable table must have a non-empty
   source_name, source_url, and retrieved_date.
2. Reachability — every distinct source_url is fetched over HTTP; a
   non-2xx/3xx response (or a request that fails outright) is flagged, since
   it means the citation is no longer verifiable by a reader clicking through.

Run manually after editing seed.py, and re-run periodically as reports age
and links rot. This does not check that the *numbers* still match the page
content — only that the citation is structurally complete and the link is
alive.
"""
import sqlite3
import sys
from pathlib import Path

import httpx

DB_PATH = Path(__file__).parent / "uae_re.db"
CITABLE_TABLES = ["market_kpis", "developers", "areas", "buyer_nationalities", "brokerages"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UAE-RE-Dashboard-SourceCheck/1.0)"}


def check_completeness(conn: sqlite3.Connection) -> list[str]:
    problems = []
    for table in CITABLE_TABLES:
        rows = conn.execute(f"SELECT rowid, * FROM {table}").fetchall()
        cols = [d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 1").description]
        for row in rows:
            record = dict(zip(cols, row[1:]))
            for field in ("source_name", "source_url", "retrieved_date"):
                if not record.get(field):
                    problems.append(f"{table} (rowid {row[0]}): missing {field}")
    return problems


def check_reachability(conn: sqlite3.Connection) -> tuple[list[str], list[str]]:
    urls: dict[str, list[str]] = {}
    for table in CITABLE_TABLES:
        cols = [d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 1").description]
        if "source_url" not in cols:
            continue
        for row in conn.execute(f"SELECT source_url FROM {table} WHERE source_url IS NOT NULL"):
            urls.setdefault(row[0], []).append(table)

    ok, failed = [], []
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        for url, tables in urls.items():
            tables_str = ", ".join(sorted(set(tables)))
            try:
                resp = client.get(url)
                if 200 <= resp.status_code < 400:
                    ok.append(f"[{resp.status_code}] {url}  (used by: {tables_str})")
                else:
                    failed.append(f"[{resp.status_code}] {url}  (used by: {tables_str})")
            except httpx.HTTPError as e:
                failed.append(f"[ERROR: {e.__class__.__name__}] {url}  (used by: {tables_str})")
    return ok, failed


def main():
    conn = sqlite3.connect(DB_PATH)

    print("== Citation completeness ==")
    problems = check_completeness(conn)
    if problems:
        for p in problems:
            print(f"  MISSING: {p}")
    else:
        print("  All rows have source_name, source_url, and retrieved_date.")

    print("\n== Source URL reachability ==")
    ok, failed = check_reachability(conn)
    for line in ok:
        print(f"  OK    {line}")
    for line in failed:
        print(f"  FAIL  {line}")

    conn.close()

    print(f"\n== Summary ==")
    print(f"  Citation gaps: {len(problems)}")
    print(f"  URLs reachable: {len(ok)} / {len(ok) + len(failed)}")

    if problems or failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
