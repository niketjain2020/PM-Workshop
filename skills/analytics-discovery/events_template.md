# Events Template — Copy & Fill

Use this template after running the Analytics Discovery skill.
Replace all `{{...}}` placeholders with your discovered data.

---

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
| | | |

### Entry Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|
| | | |

### Generation / Action Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|
| | | |

### Export / Save Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|
| | | |

### Error Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|
| | | |

### Feedback Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|
| | | |

### Credits Events
| Event | Volume (2wk) | Description |
|-------|-------------|-------------|
| | | |

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
| | | | |

## Common Mistakes

- ❌ {{Mistake 1}}
- ❌ {{Mistake 2}}

## Missing Instrumentation (Gaps)

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| | | |

## Query Examples

### Basic funnel (unique users per week)
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

### Event counts (separate query — never mix with uniqExactIf)
```sql
SELECT
  toMonday(toDate(event_time)) AS week,
  countIf(event_name = '{{entry_event}}') AS entry_events,
  countIf(event_name = '{{action_event}}') AS action_events,
  countIf(event_name = '{{export_event}}') AS export_events
FROM odsp.usage_event
WHERE dataset_name {{PLATFORM_FILTER}}
  AND toDate(event_time) >= '{{START}}'
  AND toDate(event_time) < '{{END}}'
  AND event_name IN ('{{entry_event}}','{{action_event}}','{{export_event}}')
GROUP BY week ORDER BY week
```

### Retention (7-day, entry-based)
```sql
SELECT uniqExact(user_id) as retained
FROM odsp.usage_event
WHERE dataset_name {{PLATFORM_FILTER}}
  AND toDate(event_time) >= '{{WEEK2_START}}'
  AND toDate(event_time) <= '{{WEEK2_END}}'
  AND event_name = '{{entry_event}}'
  AND user_id IN (
    SELECT user_id FROM odsp.usage_event
    WHERE dataset_name {{PLATFORM_FILTER}}
      AND toDate(event_time) >= '{{WEEK1_START}}'
      AND toDate(event_time) <= '{{WEEK1_END}}'
      AND event_name = '{{entry_event}}'
  )
```
