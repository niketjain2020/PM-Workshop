---
name: nezha-query
description: Execute custom SQL queries against Superset (Nezha) via the SQL Lab API. Use this skill when the user wants to run ClickHouse SQL queries, analyze telemetry events, explore datasets, or do data analysis on Nezha data. Supports time-series, aggregation, unique counts, and JSON field extraction queries.
---

# Nezha SQL Query Skill

Execute arbitrary SQL queries against the Superset (Nezha) ClickHouse backend
via the SQL Lab API. Authentication is handled automatically via browser SSO.

## Prerequisites
- Python 3.10+ with `requests` package
- `playwright-cli` on PATH (npm install -g @anthropic-ai/playwright-cli)
- Microsoft Edge browser (for SSO authentication)

## Quick Start

```powershell
python "<SKILL_DIR>\query.py" "<SQL_QUERY>"
```

`<SKILL_DIR>` is the directory containing this SKILL.md file.

## Setup

1. Place this skill folder in your `~/.copilot/skills/` directory (or anywhere accessible)
2. Install dependencies: `pip install requests`
3. Install playwright-cli: `npm install -g @anthropic-ai/playwright-cli`
4. On first run, a browser window will open for Microsoft SSO login
5. After initial auth, cookies are cached and refreshed automatically

## Usage Examples

### Basic query
```powershell
python "<SKILL_DIR>\query.py" "SELECT event_name, count() as cnt FROM odsp.usage_event WHERE dataset_name = 'MyDataset' AND event_time >= today() - 7 GROUP BY event_name ORDER BY cnt DESC LIMIT 20"
```

### Save results to JSON
```powershell
python "<SKILL_DIR>\query.py" "SELECT toDate(event_time) as day, uniqExact(user_id) as dau FROM odsp.usage_event WHERE dataset_name = 'MyDataset' AND event_time >= today() - 30 GROUP BY day ORDER BY day" --output "./results/dau_30d.json"
```

### Save results as CSV
```powershell
python "<SKILL_DIR>\query.py" "SELECT event_name, count() as cnt FROM odsp.usage_event WHERE dataset_name = 'MyDataset' GROUP BY event_name ORDER BY cnt DESC LIMIT 100" --output "./results/events.csv" --csv
```

### Read SQL from a file
```powershell
python "<SKILL_DIR>\query.py" --file "./queries/my_query.sql" --output "./results/output.json"
```

### Use a different database
```powershell
python "<SKILL_DIR>\query.py" "SELECT col1, col2 FROM olap.FactUsage_DAUMAU_V3 LIMIT 10" --database-id 36 --schema olap
```

### Force re-authentication
```powershell
python "<SKILL_DIR>\query.py" "SELECT 1 as test" --force-auth
```

### Increase row limit
```powershell
python "<SKILL_DIR>\query.py" "SELECT event_name FROM odsp.usage_event WHERE dataset_name = 'MyDataset' AND event_time >= today() - 1 LIMIT 5000" --limit 5000
```

---

## Available Databases

| ID | Name | Primary Table/Schema |
|----|------|---------------------|
| 301 | ODSP_CH_FEDERAL(MX) | `odsp.usage_event` (default) |
| 36 | ODSP_ADW_SPO | `olap.FactUsage_DAUMAU_V3` |
| 35 | ODSP_Nezha-Ingestion-Insights | Various ingestion tables |

---

## Query Patterns (ClickHouse SQL)

### Time-series (daily aggregation)
```sql
SELECT toDate(event_time) as day, count() as events
FROM odsp.usage_event
WHERE dataset_name = 'MyDataset'
  AND event_time >= today() - 30
GROUP BY day ORDER BY day
```

### Unique user counts (DAU/WAU/MAU)
```sql
SELECT toDate(event_time) as day, uniqExact(user_id) as dau
FROM odsp.usage_event
WHERE dataset_name = 'MyDataset'
  AND event_time >= today() - 30
GROUP BY day ORDER BY day
```

### Event breakdown by dimension
```sql
SELECT event_name, device_os_name, count() as cnt
FROM odsp.usage_event
WHERE dataset_name = 'MyDataset'
  AND event_time >= today() - 7
GROUP BY event_name, device_os_name
ORDER BY cnt DESC LIMIT 50
```

### JSON field extraction (Part C data)
```sql
SELECT 
  JSONExtractString(partc_DataBagProps, 'myKey') as extracted_value,
  count() as cnt
FROM odsp.usage_event
WHERE dataset_name = 'MyDataset'
  AND event_name = 'MyEvent'
  AND partc_DataBagProps != ''
  AND event_time >= today() - 7
GROUP BY extracted_value
ORDER BY cnt DESC LIMIT 20
```

### Table schema discovery
```sql
DESCRIBE TABLE odsp.usage_event
```

### Distinct values for a column
```sql
SELECT DISTINCT device_os_name
FROM odsp.usage_event
WHERE dataset_name = 'MyDataset'
  AND event_time >= today() - 7
```

---

## Important Notes

- **No `SELECT *`** — Superset blocks wildcard selects. Always list columns explicitly.
- **Always include time filter** — Data is partitioned by time. Queries without time filters are slow.
- **Use `count()`** not `count(*)` — ClickHouse style.
- **Use `uniqExact()`** for precise unique counts, `uniq()` for approximate (faster).
- **JSON extraction**: Use `JSONExtractString(col, 'key')`, `JSONExtractInt(col, 'key')`, etc.
- **Date functions**: `toDate()`, `today()`, `today() - N`, `toStartOfWeek()`, `toStartOfMonth()`
- **Auth refresh**: If queries fail with 401/403, the script auto-retries with fresh auth. Use `--force-auth` to force refresh manually.

---

## Dataset Reference Documentation

When working with a specific dataset, create reference documentation in your data analysis folder:

| File | Purpose |
|------|---------|
| `events.md` | Full event catalog, column reference, Part C fields, query examples |
| `instructions.md` | Methodology notes, metric definitions, platform-specific rules |

See the `sample-dataset/` folder for templates of these files.

**Always consult your dataset's reference files before writing queries.** They should contain:
- Correct `dataset_name` values (case-sensitive!)
- Qualifying events for MAU/DAU calculations
- Engagement event lists with inclusion/exclusion rules
- Known column quirks and gotchas
- Tenant column names for tenant-level analysis

---

## Error Handling

- Auth errors (401/403): Auto-retry with fresh cookies
- Query errors: Displayed with ClickHouse error message
- Timeout: Default 300s timeout for long queries

## Output Format (JSON)

```json
{
  "status": "success",
  "data": [
    {"day": "2026-06-01", "dau": 1234567},
    ...
  ],
  "columns": [
    {"column_name": "day", "type": "Date"},
    {"column_name": "dau", "type": "UInt64"}
  ],
  "row_count": 30,
  "query_info": { ... }
}
```
