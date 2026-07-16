# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A UAE real estate intelligence dashboard (Dubai only, v1). It gives investors and developers/agencies market insight — top developers, area-level price/yield trends, buyer nationality demographics, brokerage rankings — sourced from public market reports. No Node.js is used anywhere in this stack (the dev machine doesn't have it installed); all interactivity is CDN-loaded JS, no build step.

## Commands

```bash
# Setup (first time)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the dev server (auto-reloads on file changes)
source venv/bin/activate
uvicorn app.main:app --reload --port 8420
# or via the Claude Code preview tool using the "uae-re-dashboard" config in
# ../.claude/launch.json (note: launch.json lives one level up, in the parent
# working directory, not in this repo)

# Rebuild the curated dataset (drops and recreates app/db/uae_re.db)
source venv/bin/activate
python app/db/seed.py
```

There is no test suite, linter, or build step configured yet.

## Architecture

**Stack:** FastAPI (routes + Jinja2 server-rendered HTML) + SQLite (via stdlib `sqlite3`, no ORM) + Tailwind/Alpine.js/ApexCharts loaded from CDN in `templates/base.html`. This combination was chosen specifically to avoid needing Node/npm.

**Request flow:** `app/main.py` defines both page routes (`/`, `/areas`, `/developers`, `/demographics`) and JSON API routes (`/api/*-chart`) that pages fetch client-side to feed ApexCharts. Page routes call the local `query()` helper (raw SQL against `app/db/uae_re.db`, returns list-of-dict via `sqlite3.Row`) and render a Jinja2 template. There's no ORM/model layer — routes write SQL directly.

**Data model — two-tier by design, not yet fully implemented:**
- **Tier 1 (planned, not yet built):** live sync from Dubai Land Department's Dubai Pulse Open Data API for transaction-level data. Not wired up yet — waiting on DLD API credentials.
- **Tier 2 (current):** curated facts manually researched from public market reports (Property Finder, Bayut, developer ranking sites, etc.) and loaded via `app/db/seed.py`. **Every row in every curated table carries its own `source_name`, `source_url`, and `retrieved_date` columns** — this is a deliberate transparency requirement, not incidental schema design. When adding new curated data, always populate these citation columns; the UI reads and displays them (see the `source-tag` elements in the templates).

`app/db/schema.sql` defines five tables: `market_kpis`, `developers`, `areas`, `buyer_nationalities`, `brokerages`. `app/db/seed.py` is the single source of truth for what's in the database — it drops and fully recreates `uae_re.db` on every run (destructive, intentional). There are no migrations; schema changes go into `schema.sql` and `seed.py` together, then re-run `python app/db/seed.py`.

**Templates:** `base.html` is the shared shell (nav, theme toggle, CSS custom properties for the color system, `chartTokens()` JS helper). Page templates extend it and use `{% block scripts %}` to render ApexCharts instances, reading colors via `chartTokens()` so charts follow the current light/dark theme. Theme switching (`toggleTheme()` in `base.html`) persists to `localStorage` and does a full page reload rather than live-updating chart instances.

**Design system:** the color tokens in `base.html` (`--series-1` through `--series-8`, status colors, surfaces) follow a specific validated categorical palette — see the `dataviz` skill if extending charts or adding new series colors. Key rules already applied in this codebase: categorical hues assigned in fixed order (never cycled), no dual-axis charts, sequential data uses one hue ramp, every chart has a cited source rather than decorative styling.

**Secrets:** `OPENROUTER_API_KEY` (and `OPENROUTER_MODEL`) belong in `.env` (gitignored, copy from `.env.example`), loaded via `python-dotenv`. The AI Q&A/narrative-insight feature that will consume this key is not built yet — `httpx` and `python-dotenv` are installed in anticipation of it.

## Roadmap context (why some things are stubbed)

This is Phase 1 of a multi-phase plan: MVP with curated data (current state) → live DLD sync + automated monthly data refresh via a Perplexity-through-OpenRouter research agent → AI Q&A/narrative panel (OpenRouter) → polish (map views, mobile nav — the sidebar currently has no mobile fallback, `md:flex hidden`). Keep this phasing in mind before "fixing" something that's intentionally deferred (e.g., don't add live API calls to DLD without credentials being available; don't be surprised the dataset is static).
