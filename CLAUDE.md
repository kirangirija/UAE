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

# Check every curated fact has a complete citation, and that every cited
# URL is actually still reachable (hits each one over HTTP)
source venv/bin/activate
python app/db/validate_sources.py
```

There is no test suite or linter configured yet. `validate_sources.py` is the closest thing to a check — run it after editing `seed.py`.

## Architecture

**Stack:** FastAPI (routes + Jinja2 server-rendered HTML) + SQLite (via stdlib `sqlite3`, no ORM) + Tailwind/Alpine.js/ApexCharts loaded from CDN in `templates/base.html`. This combination was chosen specifically to avoid needing Node/npm. There is no local static file directory or mount — everything is CDN-loaded or inline in `base.html`; don't reintroduce `app.mount("/static", ...)` unless there's an actual local asset to serve (a previous attempt to do this crashed the deployed app, since git doesn't track empty directories — see Deployment below).

**Request flow:** `app/main.py` defines both page routes (`/`, `/areas`, `/developers`, `/demographics`) and JSON API routes (`/api/*-chart`) that pages fetch client-side to feed ApexCharts. Page routes call the local `query()` helper (raw SQL against `app/db/uae_re.db`, returns list-of-dict via `sqlite3.Row`) and render a Jinja2 template. There's no ORM/model layer — routes write SQL directly. Every page and API route requires a signed-in session (`Depends(auth.require_login)` / `Depends(auth.require_login_api)`) — see Authentication below.

**Python version gotcha:** local dev runs on the venv's Python 3.9; Render runs 3.11.9 (`PYTHON_VERSION` in `render.yaml`). `main.py` starts with `from __future__ import annotations` specifically so PEP 604 union syntax (`dict | None`) doesn't crash at import time under 3.9. If you add a new `X | None` type hint anywhere in `app/`, this is why it doesn't explode locally — don't remove that import.

**Data model — two-tier by design, not yet fully implemented:**
- **Tier 1 (planned, not yet built):** live sync from Dubai Land Department's Dubai Pulse Open Data API for transaction-level data. Not wired up yet — waiting on DLD API credentials.
- **Tier 2 (current):** curated facts manually researched from public market reports (Property Finder, Bayut, developer ranking sites, etc.) and loaded via `app/db/seed.py`. **Every row in every curated table carries its own `source_name`, `source_url`, and `retrieved_date` columns** — this is a deliberate transparency requirement, not incidental schema design. When adding new curated data, always populate these citation columns and re-run `validate_sources.py`.

`app/db/schema.sql` defines five tables: `market_kpis`, `developers`, `areas`, `buyer_nationalities`, `brokerages`. `app/db/seed.py` is the single source of truth for what's in the database — it drops and fully recreates `uae_re.db` on every run (destructive, intentional; this also happens automatically as part of the Render build command, so the deployed DB is always freshly reseeded on each deploy). There are no migrations; schema changes go into `schema.sql` and `seed.py` together, then re-run `python app/db/seed.py`.

**Source citations in the UI:** `main.py` has a `distinct_sources(rows)` helper that dedupes `(source_name, source_url, retrieved_date)` across whatever rows feed a given chart, so citations shown in the UI are always derived from the actual underlying data rather than hardcoded captions. `templates/_source_cite.html` is the shared partial that renders a `sources` list as clickable links — set `{% set sources = ... %}` then `{% include "_source_cite.html" with context %}` before a chart div. Tables (Areas, Developers, Brokerages) instead show a per-row Source column directly.

**Templates:** `base.html` is the shared shell (nav, theme toggle, CSS custom properties for the color system, `chartTokens()` JS helper). Page templates extend it and use `{% block scripts %}` to render ApexCharts instances, reading colors via `chartTokens()` so charts follow the current light/dark theme. Theme switching (`toggleTheme()` in `base.html`) persists to `localStorage` and does a full page reload rather than live-updating chart instances.

**Design system:** the color tokens in `base.html` (`--series-1` through `--series-8`, status colors, surfaces) follow a specific validated categorical palette — see the `dataviz` skill if extending charts or adding new series colors. Key rules already applied in this codebase: categorical hues assigned in fixed order (never cycled), no dual-axis charts, sequential data uses one hue ramp, every chart has a cited source rather than decorative styling.

**ApexCharts gotcha (confirmed by breaking it twice):** do not set `chart.animations.enabled: false` or `chart.redrawOnParentResize: false` on any chart in this codebase. Both were tried to fix a reported chart-jitter-on-scroll issue and both caused the chart SVG to get permanently stuck at `width="0"` on initial render — worse than the bug they were meant to fix, and it shipped broken to production once. The scroll-jitter root cause is still undiagnosed (a `MutationObserver` test found zero chart re-renders during a synthetic scroll, so the "resize-triggered redraw" theory was likely wrong to begin with). If picking this up again, reproduce it first (ideally get a screen recording from the user) before changing chart config.

**Authentication & usage analytics (`app/auth.py`):** the entire site is gated behind Google Sign-In — every page route and every `/api/*-chart` route depends on `auth.require_login` (redirects to `/login`) or `auth.require_login_api` (401 JSON), except `/healthz`, `/login`, and `/auth/*`. OAuth is handled by `authlib` (`oauth.register("google", ...)`, OIDC discovery via Google's well-known config). `main.py` builds the OAuth `redirect_uri` from the `PUBLIC_BASE_URL` env var rather than `request.url_for(...)` — this is deliberate: Render's edge proxy terminates TLS and forwards plain HTTP internally, so `request.url.scheme` can't be trusted to say `https` unless uvicorn is launched with proxy-header trust flags, which it isn't. `PUBLIC_BASE_URL` sidesteps that entirely. If you ever see a Google `redirect_uri_mismatch` error, check this env var first, not the Google Cloud Console redirect URI list.

Session state is a signed cookie (`starlette.middleware.sessions.SessionMiddleware`, needs `itsdangerous` installed and `SESSION_SECRET_KEY` set — the app raises at startup if that key is missing, on purpose, since a session cookie with no secret is a broken security boundary, not a feature to degrade gracefully). `/admin/stats` additionally requires `auth.require_admin`, which checks the signed-in email against `ADMIN_EMAIL` — this is intentionally the only account that can see who else has logged in.

**Login/usage data lives in Supabase Postgres, not local SQLite** (`SUPABASE_URL` + `SUPABASE_ANON_KEY` in `.env`, project name `uae-real-estate-dashboard`, org `kirangirija's Org`). This was a deliberate split from the curated market dataset: Render's free-tier disk is ephemeral, so anything written to local SQLite resets on every redeploy — fine for `uae_re.db` (which is meant to be re-seeded from `seed.py` every deploy anyway) but wrong for login history and stats that should accumulate over time. Access is via Supabase's REST API (PostgREST), not a raw `psycopg2`/`asyncpg` connection — no MCP tool exposes the database password or `service_role` key, only the `anon`/publishable key, so `app/auth.py` calls `httpx` against `{SUPABASE_URL}/rest/v1/...` directly (no `supabase-py` dependency needed). The `users` and `page_views` tables have permissive RLS policies scoped to the `anon` role (`create_login_analytics_tables` migration) — this is safe here because the anon/publishable key is never sent to the browser, only used server-side, and by design isn't a secret Supabase expects you to protect (it's literally named "publishable"). Login upserts (with atomic `login_count` increment) and the most-viewed-pages aggregate both go through Postgres functions exposed as PostgREST RPC endpoints (`record_login`, `page_view_counts`) rather than raw table writes, since PostgREST's REST upsert semantics don't support "increment on conflict" and its querystring API doesn't support arbitrary `GROUP BY`. `record_login`/`record_page_view` swallow `httpx.HTTPError` and log rather than raising — a Supabase hiccup shouldn't break someone's ability to view the dashboard, since these are non-critical side effects.

**Secrets:** `.env` (gitignored, copy from `.env.example`) holds: `OPENROUTER_API_KEY`/`OPENROUTER_MODEL` (unused — see below), `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` (from Google Cloud Console, OAuth 2.0 Client for "UAE Real Estate Intelligence"), `SESSION_SECRET_KEY` (any long random string, `python3 -c "import secrets; print(secrets.token_hex(32))"`), `ADMIN_EMAIL`, `PUBLIC_BASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`. `OPENROUTER_API_KEY` (and `OPENROUTER_MODEL`) are for the not-yet-built AI Q&A/narrative-insight feature — `httpx` and `python-dotenv` are installed in anticipation of it. Don't add `OPENROUTER_API_KEY` back to `render.yaml`'s `envVars` until that feature actually reads it (it was added prematurely once and removed).

## Deployment

Live at **https://uae-real-estate-dashboard.onrender.com** (Render free tier — sleeps after ~15 min idle, ~30-60s cold start on next request). Source of truth is the GitHub repo **github.com/kirangirija/UAE**, `main` branch. `render.yaml` is a Render Blueprint: build command installs deps and runs `seed.py`, start command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. `healthCheckPath` is `/healthz`, not `/` — the whole site requires login now, and a health check that gets redirected to `/login` would read as unhealthy.

**Env vars on an already-deployed service don't self-provision.** `render.yaml` marks `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `SESSION_SECRET_KEY` as `sync: false` (Render's way of saying "don't commit this value, prompt for it instead") — but that auto-prompt only fires the *first* time a Blueprint creates a service. For an existing service, newly added `sync: false` vars have to be added by hand in the Render dashboard's Environment tab. `SUPABASE_URL` and `SUPABASE_ANON_KEY` are committed as plain `value:` entries instead, since the anon/publishable key is explicitly designed by Supabase to be safe to ship (access is scoped by RLS, not key secrecy) — no manual dashboard step needed for those two.

**Git workflow quirk:** this dev machine has no `gh` CLI and no working git credential helper for GitHub over HTTPS (`git push` fails with "could not read Username" — confirmed, not just untried). Commits should still be made locally with `git commit` as normal, but **pushing requires the user to do it via GitHub Desktop** (already configured, points at the `UAE` repo). After committing, tell the user to open GitHub Desktop and click "Push origin" — don't assume `git push` will work from a Bash tool call.

## Roadmap context (why some things are stubbed)

This is Phase 1 of a multi-phase plan: MVP with curated data (current state, now deployed) → live DLD sync + automated monthly data refresh via a Perplexity-through-OpenRouter research agent → AI Q&A/narrative panel (OpenRouter) → polish (map views, mobile nav — the sidebar currently has no mobile fallback, `md:flex hidden`). Keep this phasing in mind before "fixing" something that's intentionally deferred (e.g., don't add live API calls to DLD without credentials being available; don't be surprised the dataset is static).
