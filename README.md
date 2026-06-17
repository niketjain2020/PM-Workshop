# PM Workshop

Claude Code skills for product management workflows.

## Skills

| Skill | Description |
|-------|-------------|
| [analytics-discovery](./skills/analytics-discovery/) | Discover telemetry for any product feature by inspecting Superset dashboards, running direct SQL event discovery, auto-categorizing events, and generating a structured events.md file. |
| [nezha-query](./skills/nezha-query/) | Execute arbitrary ClickHouse SQL queries against Superset (Nezha) via the SQL Lab API. Browser-based SSO auth with automatic cookie refresh. Supports JSON/CSV output, batch queries, and multiple databases. |

## Usage

Copy the skill folder to your project's `.claude/skills/` directory:

```bash
cp -r skills/<skill-name> /path/to/project/.claude/skills/
```

Or install to your user-level skills (available in all projects):

```bash
cp -r skills/<skill-name> ~/.copilot/skills/
```

## Prerequisites

### nezha-query
- Python 3.10+ with `requests` package
- `playwright-cli` on PATH (`npm install -g @anthropic-ai/playwright-cli`)
- Microsoft Edge browser (for SSO authentication)
- Access to [Superset (Nezha)](https://www.microsoftnezha.com)

### analytics-discovery
- Requires the `nezha-query` skill to be installed (used for SQL execution)
- Python 3.10+
