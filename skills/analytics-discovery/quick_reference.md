# Analytics Discovery — Quick Reference Card

## The 3-Minute Version

```
1. Pick a feature + platform
2. Get keywords (from dashboard or your head)
3. Run: SELECT DISTINCT event_name, count() ... WHERE event_name ILIKE '%keyword%'
4. Categorize results → build funnel
5. Check gaps → document in events.md
```

## Auth Snippet (run first)

```javascript
// Navigate to https://www.microsoftnezha.com/sqllab/ then run:
async () => {
  const r = await fetch('/api/v1/security/csrf_token/', { credentials: 'include' });
  const d = await r.json();
  window.__csrf = d.result;
  return d.result ? 'OK' : 'NEEDS_LOGIN';
}
```

## Discovery Query Template

```sql
SELECT DISTINCT event_name, count() as volume
FROM odsp.usage_event
WHERE toDate(event_time) >= today() - 14
  AND toDate(event_time) < today()
  AND dataset_name = '{{PLATFORM}}'
  AND event_name ILIKE '%{{KEYWORD}}%'
GROUP BY event_name
ORDER BY volume DESC
LIMIT 100
```

**Platform values:**
| Platform | dataset_name |
|----------|-------------|
| iOS | `'iOS'` |
| Android | `IN ('Android','SPOAndroid')` |
| Web | `IN ('SPOWeb','ODCWeb')` |

## Execute Query via API

```javascript
async () => {
  const csrf = window.__csrf;
  const sql = `YOUR QUERY HERE`;
  const r = await fetch('/api/v1/sqllab/execute/', {
    method: 'POST', credentials: 'include',
    headers: {'Content-Type':'application/json','X-CSRFToken': csrf},
    body: JSON.stringify({ database_id: 301, schema: 'odsp', sql, runAsync: false, queryLimit: 200 })
  });
  return JSON.stringify((await r.json()).data);
}
```

## Category Cheat Sheet

| Category | Look for these words in event names |
|----------|-------------------------------------|
| Discovery | FRE, Shown, Visible, Banner, Highlight, Popover |
| Entry | Open, Click, Launch, Entered, Start |
| Interaction | Selected, Clicked, Toggled, Tab, Zoom, Scroll |
| Generation | Generate, Submit, Process, Creation, Request |
| Export | Save, Download, Copy, Share, Keep, Kept |
| Editing | Undo, Redo, Reset, Brush, Edit, Draw |
| Error | Error, Failed, Violation, Moderation, Offline |
| Cancel | Cancel, Stop, Exit, Dismiss, Discard |
| Feedback | Like, Dislike, Feedback, Rating |
| Credits | Credit, Upsell, Exhausted, Insufficient |

## Gap Checklist

```
□ Discovery/FRE event exists?
□ Entry/open event exists?
□ Primary action event exists?
□ Explicit SUCCESS event (not just attempt)?
□ Failure/error event exists?
□ Export/save event exists?
□ Feedback (like/dislike) event exists?
□ Same stages tracked on all platforms?
```

## Critical Rules

1. **Never mix `uniqExactIf` and `countIf`** in one query — ClickHouse errors
2. **Keep queries under 2KB** — proxy limit
3. **Use `toDate(event_time)`** — no `event_date` column
4. **Database ID: 301, Schema: odsp** — always
5. **Volume = 0 → probably deprecated** — don't include in events.md
