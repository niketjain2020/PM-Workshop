---
name: analytics-discovery
version: 1.0.0
description: Discover telemetry for any product feature by inspecting Superset dashboards, running direct SQL event discovery, auto-categorizing events, and generating a structured events.md file ready for funnel/retention/health analysis.
---

# Analytics Discovery & Event Definition

## Overview

Help a user discover telemetry for a specific product area/feature by:
1. Extracting context from Superset dashboards (keywords, filters, chart titles)
2. Running direct SQL discovery queries against ClickHouse
3. Auto-categorizing events into funnel stages
4. Validating coverage gaps
5. Generating a structured `events.md` file

The output `events.md` becomes the foundation for all downstream analysis (funnels, retention, MBRs).

## Keywords

discovery, events, telemetry, event definition, instrumentation, events.md, discover events, what events, coverage, gaps, missing events, feature telemetry, dashboard

## Before Starting, Ask

### 1. Feature Area (Required)

> Which feature or product area do you want to analyze? Keep it scoped (e.g., "onboarding", "search", "AI Restyle", "checkout") rather than the full product.

### 2. Platform(s) (Required)

> Which platform(s)? Options: iOS, Android, Web, or All.

### 3. Superset Dashboard Link(s) (Recommended, not required)

> Share 1-3 relevant Superset dashboard links for this feature. If you don't have dashboards, provide 2-3 keyword patterns to search for (e.g., "Copilot", "Loop", "Restyle").

### 4. Business Context (Optional)

> Any specific question or KPI you're focused on? (e.g., drop in engagement, funnel conversion, retention, activation, feature adoption)

Do not proceed until feature area and platform are provided. Dashboard links OR keywords must be provided — one or the other.

---

## Execution Flow

### Step 1: Verify Auth & Connection

1. Navigate to `https://www.microsoftnezha.com/sqllab/`
2. Retrieve CSRF token:

```js
async () => {
  const r = await fetch('/api/v1/security/csrf_token/', { credentials: 'include' });
  const d = await r.json();
  window.__csrf = d.result;
  return d.result ? 'OK' : 'NEEDS_LOGIN';
}
```

3. If `NEEDS_LOGIN`: prompt user to log in manually, then retry.

**Output:** `Auth Status: ✅ Connected` or `❌ Needs Login`

---

### Step 2: Extract Keywords from Dashboard (if provided)

If user provided dashboard links:

1. Navigate to dashboard URL
2. Wait for charts to load (~6 seconds)
3. Extract from the page:
   - Chart titles (visible text via `.editable-title span`, `.header-title span`)
   - Filter bar values (dataset names, date ranges)
   - Any visible event names or metric labels
4. Build a keyword list from extracted text

If user provided keywords directly, skip this step.

**Output:** List of 3-10 search keywords/patterns for Step 3.

---

### Step 2b: View Query on 2-3 Key Charts (if dashboard provided)

After extracting keywords, open "View Query" on 2-3 of the most relevant charts (preferably funnel charts, breakdown charts, or the most complex ones). This reveals:
- **Property columns** used for breakdowns (not discoverable via keyword search alone)
- **Filter logic** (scenario IDs, special conditions)
- **Event combinations** the dashboard author intentionally grouped
- **Sampling** (SAMPLE 0.1 = estimates ×10)

#### Reliable DOM pattern:

```js
async () => {
  // 1. Find chart container
  const chart = document.querySelector('[data-test-chart-id="{{CHART_ID}}"]');
  
  // 2. Hover to reveal controls
  chart.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
  await new Promise(r => setTimeout(r, 800));
  
  // 3. Click "More Options" (three dots)
  const moreBtn = chart.querySelector('[aria-label="More Options"].ant-dropdown-trigger');
  moreBtn.click();
  await new Promise(r => setTimeout(r, 1000));
  
  // 4. Click "View query" in dropdown
  const dropdowns = document.querySelectorAll('.ant-dropdown:not(.ant-dropdown-hidden)');
  const dd = dropdowns[dropdowns.length - 1];
  const items = dd.querySelectorAll('li, [role=menuitem], .ant-dropdown-menu-item');
  const viewQuery = [...items].find(i => i.textContent.trim() === 'View query');
  viewQuery.click();
  await new Promise(r => setTimeout(r, 2500));
  
  // 5. Read SQL from modal
  const modals = document.querySelectorAll('.ant-modal, [role=dialog]');
  const modal = modals[modals.length - 1];
  return modal.innerText;  // Contains the full SQL query
}
```

#### How to find chart IDs:

```js
// List all chart IDs on the dashboard
const charts = document.querySelectorAll('[data-test-chart-id]');
[...charts].map(c => c.getAttribute('data-test-chart-id'));
```

#### After reading query, close modal:

```js
document.querySelector('.ant-modal .ant-modal-close, .ant-modal-close-x')?.click();
```

#### What to extract from View Query results:

| Look for | Why |
|----------|-----|
| `partc_*` columns in SELECT or WHERE | Property breakdowns (e.g., `partc_Engagement_extraData_scenarioId`) |
| Multiple event names in OR conditions | Dashboard author's intentional event groupings |
| SAMPLE clauses | Dashboard uses estimates (multiply by 1/sample_rate) |
| Specific filter values (e.g., `= 'SendPageAsEmail'`) | Critical filters to isolate this feature from broader events |

**Limit to 2-3 charts** — more than that is diminishing returns. Pick charts that appear to have breakdowns/filters (funnel charts, pivot tables, charts with "by Type/Source" in their title).

**If View Query fails** (modal empty, button not found), skip and proceed to Step 3 — keyword discovery always works.

**Output:** Property columns, filter logic, and any additional event names not in the keyword list.

---

### Step 3: Direct SQL Event Discovery

This is the core technique. Run discovery queries using keywords from Step 2.

#### 3a. Discover event names by keyword

For each keyword pattern, run:

```js
async () => {
  const csrf = window.__csrf;
  const sql = `SELECT DISTINCT event_name, count() as volume
    FROM odsp.usage_event
    WHERE toDate(event_time) >= '{{2_WEEKS_AGO}}'
      AND toDate(event_time) < '{{TODAY}}'
      AND dataset_name {{PLATFORM_FILTER}}
      AND event_name ILIKE '%{{KEYWORD}}%'
    GROUP BY event_name
    ORDER BY volume DESC
    LIMIT 100`;
  const r = await fetch('/api/v1/sqllab/execute/', {
    method: 'POST', credentials: 'include',
    headers: {'Content-Type':'application/json','X-CSRFToken': csrf},
    body: JSON.stringify({ database_id: 301, schema: 'odsp', sql, runAsync: false, queryLimit: 200 })
  });
  return JSON.stringify((await r.json()).data);
}
```

**Platform filters:**
- iOS: `= 'iOS'`
- Android: `IN ('Android','SPOAndroid')`
- Web: `IN ('SPOWeb','ODCWeb')`
- All: omit filter (but add `dataset_name` to GROUP BY)

#### 3b. If >100 results, narrow scope

Add additional filters:
- Platform-specific `dataset_name`
- Exclude known unrelated prefixes
- Filter by minimum volume (`HAVING count() > 50`)

#### 3c. Discover properties for high-value events

For top 5-10 events by volume, discover non-empty property columns:

```sql
SELECT
  event_name,
  countIf(partc_Type != '') as has_type,
  countIf(partc_Source != '') as has_source,
  countIf(partc_CopilotActionType != '') as has_copilot_action,
  countIf(partc_EventName != '') as has_subevent
FROM odsp.usage_event
WHERE toDate(event_time) >= '{{1_WEEK_AGO}}'
  AND event_name = '{{EVENT_NAME}}'
  AND dataset_name {{PLATFORM_FILTER}}
GROUP BY event_name
```

**Keep queries under 2KB** — ClickHouse proxy limit.

**Output:** Raw event list with volumes.

---

### Step 4: Auto-Categorize Events

Categorize each discovered event into one of these standard categories:

| Category | Description | Naming Signals |
|----------|-------------|----------------|
| **Discovery** | User sees/discovers the feature | FRE, Shown, Visible, Banner, Highlight |
| **Entry** | User opens/enters the feature | Open, Click, Launch, Entered |
| **Interaction** | In-feature actions (not generation) | Selected, Clicked, Toggled, Tab, Zoom |
| **Generation** | AI/compute action triggered | Generate, Submit, Process, Creation |
| **Export** | User saves/exports output | Save, Download, Copy, Share, Keep, Kept |
| **Editing** | Undo/redo/modify within feature | Undo, Redo, Reset, Brush, Edit |
| **Error** | Failures, blocks, violations | Error, Failed, Violation, Moderation, Offline |
| **Cancellation** | User abandons action | Cancel, Stop, Exit, Dismiss, Discard |
| **Feedback** | Explicit user sentiment | Like, Dislike, Feedback, Rating |
| **Credits** | Usage limits, upsells | Credit, Upsell, Exhausted, Insufficient |
| **System** | Internal/infra events | Notification, Compression, Restore, Socket |
| **Navigation** | Movement between views | Exit, Back, TabSwitch, Close |

Present the categorized list to the user as a table sorted by category → volume.

**Output:** Categorized event table.

---

### Step 5: Validate & Confirm with User

Present the categorized events and ask:

> Here's what I found for [feature] on [platform]. Before I generate the events.md:
> 1. Do these categories look right? Anything miscategorized?
> 2. Are there events you expected to see that are missing?
> 3. Which events form your core funnel (ordered)?

**Do NOT skip this step.** User validation prevents incorrect funnel ordering and misclassification.

---

### Step 6: Gap Analysis

Check for completeness using this checklist:

```
Coverage Check:
✅/❌ Has discovery/FRE event?
✅/❌ Has entry/open event?
✅/❌ Has primary action event (generation, submission, etc.)?
✅/❌ Has SUCCESS event (explicit, not just attempt)?
✅/❌ Has FAILURE/error event?
✅/❌ Has export/save event?
✅/❌ Has user feedback event (like/dislike)?
✅/❌ Has cancellation event?
✅/❌ Has credit/limit tracking?

Platform Parity:
✅/❌ Same funnel stages tracked on all requested platforms?
✅/❌ Event naming consistent across platforms?
✅/❌ Save mechanism equivalent across platforms?
```

Flag gaps explicitly. Recommend instrumentation additions where needed.

---

### Step 7: Generate `events.md`

Generate the file using the template below. Save to the user's workspace (ask where if unclear).

**File location convention:** `events/{feature_name}_{platform}_events.md`
(e.g., `events/copilot_ios_events.md`)

---

## `events.md` Template

```markdown
# Feature: {{FEATURE_NAME}} — {{PLATFORM}} Events

## Objective
{{One sentence: what this feature does for users}}

## Quick Reference

| Step | Event Name | Volume (2wk) |
|------|-----------|--------------|
| Discovery | {{...}} | {{...}} |
| Entry | {{...}} | {{...}} |
| Action | {{...}} | {{...}} |
| Export | {{...}} | {{...}} |

## Platform Differences (CRITICAL)

| | Platform A | Platform B | Platform C |
|--|-----------|-----------|-----------|
| **Event namespace** | {{...}} | {{...}} | {{...}} |
| **Event filter** | {{...}} | {{...}} | {{...}} |
| **dataset_name** | {{...}} | {{...}} | {{...}} |
| **Save mechanism** | {{...}} | {{...}} | {{...}} |
| **Known quirks** | {{...}} | {{...}} | {{...}} |

## Full Event Catalog

### Discovery Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|
| {{...}} | {{...}} | {{...}} |

### Entry Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|

### Interaction Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|

### Generation / Action Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|

### Export / Save Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|

### Error Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|

### Feedback Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|

### Credits Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|

### System / Navigation Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|

## Funnel Definition

| Step | Event | Users (weekly) | Conversion |
|------|-------|---------------|-----------|
| 1. Discovery | {{...}} | {{...}} | — |
| 2. Entry | {{...}} | {{...}} | {{X}}% |
| 3. Action | {{...}} | {{...}} | {{X}}% |
| 4. Export | {{...}} | {{...}} | {{X}}% |

E2E conversion: {{X}}%

## Key Properties

| Event | Property | Values | Use |
|-------|----------|--------|-----|
| {{...}} | partc_Type | {{...}} | Style/variant breakdown |
| {{...}} | partc_Source | {{...}} | Entry point attribution |

## Common Mistakes

- ❌ Don't use `{{wrong_pattern}}` — that's {{other_platform}}. Use `{{correct_pattern}}`.
- ❌ Don't filter `dataset_name = '{{wrong}}'` — correct value is `'{{correct}}'`.
- ❌ {{Any known logging gaps or date ranges with bad data}}

## Missing Instrumentation (Gaps)

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| No explicit success event | Can't compute failure rate | Add `{{feature}}.ActionSuccess` |
| {{...}} | {{...}} | {{...}} |

## Query Examples

### Basic funnel (users)
```sql
SELECT
  toMonday(toDate(event_time)) AS week,
  uniqExactIf(user_id, event_name = '{{entry_event}}') AS entered,
  uniqExactIf(user_id, event_name = '{{action_event}}') AS acted,
  uniqExactIf(user_id, event_name = '{{export_event}}') AS exported
FROM odsp.usage_event
WHERE dataset_name {{PLATFORM_FILTER}}
  AND toDate(event_time) >= '{{START}}'
  AND toDate(event_time) < '{{END}}'
  AND event_name IN ('{{entry_event}}','{{action_event}}','{{export_event}}')
GROUP BY week ORDER BY week
```

### Event counts (do NOT mix with uniqExactIf)
```sql
SELECT
  toMonday(toDate(event_time)) AS week,
  countIf(event_name = '{{entry_event}}') AS entry_events,
  countIf(event_name = '{{action_event}}') AS action_events
FROM odsp.usage_event
WHERE dataset_name {{PLATFORM_FILTER}}
  AND toDate(event_time) >= '{{START}}'
  AND toDate(event_time) < '{{END}}'
  AND event_name IN ('{{entry_event}}','{{action_event}}')
GROUP BY week ORDER BY week
```
```

---

## Guardrails

1. **Always ask for feature area + platform** before starting.
2. **Keep scoped** — one feature area, not the full product.
3. **Hybrid approach**: keyword discovery first (fast, complete), then View Query on 2-3 charts (reveals properties & filters).
4. **Never mix `uniqExactIf` and `countIf`** in the same query — ClickHouse distributed engine errors.
5. **Keep queries under ~2KB** — proxy body size limit causes HTTP 500.
6. **Use `toDate(event_time)`** for date filtering — no `event_date` column exists.
7. **Always validate with user** before generating events.md — don't assume funnel ordering.
8. **Don't trust event names alone** — verify with volume. Zero-volume events may be deprecated.
9. **Database ID: 301, Schema: odsp** — always use these values for Superset API calls.
10. **If dashboard is inaccessible**, fall back to keyword-based discovery (never block on dashboard).
11. **View Query limit: 2-3 charts max** — pick funnel, breakdown, or "by Type" charts. More is diminishing returns.
12. **Watch for SAMPLE clauses** in View Query results — dashboard may show estimates (×10, ×100). Note this in events.md.

## Timing Guide (for workshop use)

| Step | Duration | Notes |
|------|----------|-------|
| Inputs | 2 min | Feature + platform + keywords |
| Auth | 1 min | CSRF token |
| Dashboard keywords | 2 min | Chart titles, filter labels |
| View Query (2-3 charts) | 2 min | Properties, filters, event combos |
| SQL discovery | 5 min | The core technique — bulk event names |
| Auto-categorize | 2 min | Present table to user |
| User validation | 5 min | Critical — don't skip |
| Gap analysis | 3 min | Checklist review |
| Generate events.md | 3 min | Save to workspace |
| **Total** | **~25 min** | |
