# PM Workshop

Claude Code skills and workshop materials for product management workflows — from data question to shareable insight in minutes.

## Workshop

📄 **[Agency Copilot Workshop Agenda](./workshop/agency_copilot_workshop_agenda.docx)** — 90-minute hands-on session

### What You'll Learn

| Time | Block | Format |
|------|-------|--------|
| 0:00–0:20 | **Setup** — Install, connect to data source, first query | Follow along |
| 0:20–1:10 | **3 Workflows** — System health, experiment analysis, decision deep-dives | Demo + try it |
| 1:10–1:30 | **Takeaways** — Prompt templates, daily habits, skill sharing | Discussion |

### The Three Workflows

| Workflow | What It Replaces |
|----------|-----------------|
| **A. System Health & Telemetry** | Morning dashboard checks → conversational queries |
| **B. Experimentation & A/B Analysis** | Waiting for DS queue → instant experiment reads |
| **C. Business Decision Deep-Dives** | "Something looks off" → shareable investigation in minutes |

### Pre-Workshop Setup

1. Install Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
2. Authenticate with GitHub
3. Create project folder with `.mcp.json` (Playwright MCP)
4. Write `CLAUDE.md` with your data source context
5. Verify: agent can navigate to your data tool

See the [full agenda document](./workshop/agency_copilot_workshop_agenda.docx) for detailed setup steps, discovery queries, starter prompts, and the five daily habits to adopt.

---

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
