"""Execute SQL queries against Superset (Nezha) via the SQL Lab API.

Self-contained query engine using browser-based authentication via playwright-cli.
Queries are executed through the browser's XHR to leverage HttpOnly session cookies.

Usage:
    python query.py "<SQL>" [--database-id 301] [--schema odsp] [--limit 1000] [--output file.json]
    python query.py --file query.sql [--output results.json]

Examples:
    python query.py "SELECT event_name, count() as cnt FROM odsp.usage_event WHERE dataset_name = 'MyDataset' GROUP BY event_name ORDER BY cnt DESC LIMIT 20"
    python query.py "SELECT toDate(event_time) as day, uniqExact(user_id) as dau FROM odsp.usage_event WHERE dataset_name = 'MyDataset' AND event_time >= today() - 30 GROUP BY day ORDER BY day" --output dau.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR))
from auth import ensure_browser_session

API_BASE = "https://www.microsoftnezha.com/api/v1"
DEFAULT_DATABASE_ID = 301  # ODSP_CH_FEDERAL(MX)
DEFAULT_SCHEMA = "odsp"
BROWSER_SESSION = "superset"


def _pw(*args: str, timeout: int = 120) -> str:
    """Run a playwright-cli command. Returns stdout+stderr."""
    # Use shell=True for Windows .cmd resolution, but quote args properly
    quoted_args = []
    for arg in args:
        if ' ' in arg or '"' in arg or "'" in arg or any(c in arg for c in '|&<>^'):
            # Wrap in double quotes, escape internal double quotes
            quoted_args.append('"' + arg.replace('"', '\\"') + '"')
        else:
            quoted_args.append(arg)
    cmd = f'playwright-cli -s={BROWSER_SESSION} {" ".join(quoted_args)}'
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, shell=True,
    )
    return result.stdout + result.stderr


def _get_csrf_token() -> str:
    """Get CSRF token by navigating browser to the CSRF endpoint."""
    _pw("open", f"{API_BASE}/security/csrf_token/")
    time.sleep(2)
    body = _pw("eval", "document.body.innerText")
    # Output format: ### Result\n"{\"result\":\"<token>\"}\n"
    # Unescape the JSON string escapes
    unescaped = body.replace('\\"', '"').replace('\\n', '')
    m = re.search(r'"result"\s*:\s*"([^"]+)"', unescaped)
    if m:
        return m.group(1)
    raise RuntimeError(f"Could not extract CSRF token from: {body[:300]}")


def execute_query(
    sql: str,
    database_id: int = DEFAULT_DATABASE_ID,
    schema: str = DEFAULT_SCHEMA,
    limit: int = 1000,
    force_auth: bool = False,
) -> dict:
    """Execute a SQL query via Superset SQL Lab API using browser XHR.

    Returns dict with keys: status, data, columns, query_info, error
    """
    # Ensure browser session is authenticated
    ensure_browser_session(force=force_auth)

    # Get CSRF token
    csrf = _get_csrf_token()

    # Build synchronous XHR to execute query (uses browser's HttpOnly cookies)
    payload_json = json.dumps({
        "database_id": database_id,
        "sql": sql,
        "schema": schema,
        "runAsync": False,
        "queryLimit": limit,
    })
    # Base64 encode payload to avoid all quoting/escaping issues
    import base64
    payload_b64 = base64.b64encode(payload_json.encode()).decode()

    js_code = (
        f"(function(){{var x=new XMLHttpRequest();"
        f"x.open('POST','/api/v1/sqllab/execute/',false);"
        f"x.setRequestHeader('Content-Type','application/json');"
        f"x.setRequestHeader('X-CSRFToken','{csrf}');"
        f"x.send(atob('{payload_b64}'));"
        f"return JSON.stringify({{s:x.status,b:x.responseText}})"
        f"}})()"
    )

    raw = _pw("eval", js_code)

    # Parse result from playwright-cli output: ### Result\n"<json-string>"
    result_match = re.search(r'### Result\s*\n(.*)', raw, re.DOTALL)
    if not result_match:
        return {"status": "error", "error": f"No result from eval: {raw[:300]}", "data": [], "columns": []}

    raw_value = result_match.group(1).strip()
    # The value is a JSON-encoded string (e.g., "{\"s\":200,\"b\":\"...\"}")
    try:
        outer = json.loads(raw_value)  # Decode the JSON string wrapper
    except json.JSONDecodeError:
        # Fallback: strip quotes and unescape manually
        outer = raw_value.strip('"').replace('\\"', '"').replace('\\\\', '\\')

    # Parse the wrapper object {s: status, b: body}
    try:
        parsed = json.loads(outer) if isinstance(outer, str) else outer
        http_status = int(parsed.get("s", 0))
        response_body = parsed.get("b", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return {"status": "error", "error": f"Could not parse XHR response: {str(outer)[:300]}", "data": [], "columns": []}

    if http_status in [401, 403] and not force_auth:
        print("Auth expired, refreshing...")
        return execute_query(sql, database_id, schema, limit, force_auth=True)

    if http_status != 200:
        error_msg = ""
        try:
            err = json.loads(response_body)
            errors = err.get("errors", [])
            if errors:
                error_msg = errors[0].get("message", str(err))
            else:
                error_msg = str(err)
        except Exception:
            error_msg = response_body[:500]
        return {"status": "error", "error": error_msg, "http_status": http_status, "data": [], "columns": []}

    try:
        result = json.loads(response_body)
    except json.JSONDecodeError as e:
        return {"status": "error", "error": f"JSON parse error: {e}", "data": [], "columns": []}

    status = result.get("status", "unknown")
    if status == "success":
        return {
            "status": "success",
            "data": result.get("data", []),
            "columns": result.get("columns", []),
            "query_info": result.get("query", {}),
            "row_count": len(result.get("data", [])),
        }
    else:
        return {
            "status": status,
            "error": result.get("msg", str(result.get("errors", ""))),
            "data": [],
            "columns": [],
        }


def main():
    parser = argparse.ArgumentParser(
        description="Execute SQL queries against Superset (Nezha)."
    )
    parser.add_argument("sql", nargs="?", help="SQL query to execute")
    parser.add_argument("--file", "-f", help="Read SQL from file")
    parser.add_argument("--database-id", "-d", type=int, default=DEFAULT_DATABASE_ID,
                        help=f"Database ID (default: {DEFAULT_DATABASE_ID})")
    parser.add_argument("--schema", "-s", default=DEFAULT_SCHEMA,
                        help=f"Schema (default: {DEFAULT_SCHEMA})")
    parser.add_argument("--limit", "-l", type=int, default=1000,
                        help="Row limit (default: 1000)")
    parser.add_argument("--output", "-o", help="Output file (JSON)")
    parser.add_argument("--force-auth", action="store_true",
                        help="Force re-authentication")
    parser.add_argument("--csv", action="store_true",
                        help="Output as CSV instead of JSON")
    args = parser.parse_args()

    # Get SQL
    if args.file:
        sql = Path(args.file).read_text(encoding="utf-8").strip()
    elif args.sql:
        sql = args.sql
    else:
        parser.error("Provide SQL as argument or via --file")
        return

    print(f"Executing query (limit={args.limit}, db={args.database_id})...")
    print(f"SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}")
    print()

    start = time.time()
    result = execute_query(
        sql=sql,
        database_id=args.database_id,
        schema=args.schema,
        limit=args.limit,
        force_auth=args.force_auth,
    )
    elapsed = time.time() - start

    if result["status"] != "success":
        print(f"ERROR: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    rows = result["data"]
    print(f"Success: {len(rows)} rows returned in {elapsed:.1f}s")

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if args.csv:
            import csv
            if rows:
                with open(output_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
            print(f"Saved CSV to {output_path}")
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"Saved JSON to {output_path}")
    else:
        # Print to stdout
        if rows:
            cols = list(rows[0].keys())
            print("\n" + " | ".join(cols))
            print("-" * (sum(len(c) for c in cols) + 3 * (len(cols) - 1)))
            for row in rows[:20]:
                values = [str(row.get(c, ""))[:40] for c in cols]
                print(" | ".join(values))
            if len(rows) > 20:
                print(f"... ({len(rows) - 20} more rows)")


if __name__ == "__main__":
    main()
