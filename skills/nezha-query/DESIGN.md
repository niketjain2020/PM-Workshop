# Superset SQL Lab API — Design Reference

## Overview

This skill executes custom SQL queries against Superset (Nezha) via the SQL Lab
API. Authentication uses browser-based SSO with persistent cookie storage.

---

## API Details

### Base URL

- **API Base**: `https://www.microsoftnezha.com/api/v1`
- **Superset path prefix**: `/nezha` (for UI pages only, API is at root)
- **Auth cookies domain**: `www.microsoftnezha.com`

### SQL Lab Execute Endpoint

```
POST /api/v1/sqllab/execute/
```

**Request body:**
```json
{
  "database_id": 301,
  "sql": "SELECT event_name, count() as cnt FROM odsp.usage_event WHERE dataset_name = 'MyDataset' GROUP BY event_name LIMIT 10",
  "schema": "odsp",
  "runAsync": false,
  "queryLimit": 1000
}
```

**Required headers:**
- Cookie: `session=<value>` (from auth)
- X-CSRFToken: `<csrf_token>` (from `/api/v1/security/csrf_token/`)
- Referer: `https://www.microsoftnezha.com/nezha/`
- Accept: `application/json`
- Content-Type: `application/json`

**Response (success):**
```json
{
  "status": "success",
  "data": [
    {"event_name": "MyEvent", "cnt": 1108498490},
    ...
  ],
  "columns": [
    {"column_name": "event_name", "type": "String", ...},
    {"column_name": "cnt", "type": "UInt64", ...}
  ],
  "query": {
    "changedOn": "...",
    "dbId": 301,
    "executedSql": "...",
    "rows": 10,
    "state": "success"
  }
}
```

**Known constraints:**
- `SELECT *` is **not allowed** — must specify columns explicitly
- Queries are subject to a row limit (default queryLimit applies)
- Auth errors return 401/403 — retry with fresh auth

### CSRF Token Endpoint

```
GET /api/v1/security/csrf_token/
```

Returns: `{"result": "<token>"}`

### Other Useful Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/database/` | GET | List available databases |
| `/api/v1/dataset/?q=(page:0,page_size:50)` | GET | List datasets |
| `/api/v1/chart/{id}/data/` | GET | Fetch saved chart data |
| `/api/v1/dashboard/{id}/charts` | GET | List charts in dashboard |

---

## Database & Schema Details

### Available Databases

| ID | Name | Use |
|----|------|-----|
| 301 | ODSP_CH_FEDERAL(MX) | Main ClickHouse — usage_event table |
| 36 | ODSP_ADW_SPO | ADW — FactUsage_DAUMAU_V3 |
| 35 | ODSP_Nezha-Ingestion-Insights | Ingestion monitoring |

### Target Table: `odsp.usage_event`

- **Database ID**: 301
- **Schema**: odsp
- **Engine**: ClickHouse
- **Total columns**: 2,266 (115 standard + 2,151 partc_ columns)
- **Key filter**: `dataset_name = '<your_dataset>'`

---

## Authentication Strategy

1. Load cookies from `.auth/state.json` (in skill directory)
2. Validate via CSRF token endpoint
3. If expired, open browser via `playwright-cli` for SSO re-auth
4. Include CSRF token in `X-CSRFToken` header for POST requests

The persistent Edge profile at `%LOCALAPPDATA%\NezhaAuth\EdgeProfile` retains
Microsoft SSO cookies across sessions, enabling automatic re-authentication
without manual login.

---

## ClickHouse SQL Notes

- Use `toDate(event_time)` for daily grouping
- Use `uniqExact(user_id)` for exact unique counts (vs `uniq()` for approx)
- Use `today()` for current date, `today() - N` for N days ago
- Use `JSONExtractString(col, 'key')` to parse JSON fields
- Always include time filter for performance (data is partitioned by time)
- `SELECT *` is disabled — must enumerate columns
- `count()` instead of `count(*)` (ClickHouse style)
