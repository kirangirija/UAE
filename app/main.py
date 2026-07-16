from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app import auth

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "db" / "uae_re.db"

SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY")
if not SESSION_SECRET_KEY:
    raise RuntimeError(
        "SESSION_SECRET_KEY is not set. Add it to .env locally (any long random "
        "string) and to the Render service's environment variables in production."
    )
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8420").rstrip("/")

app = FastAPI(title="UAE Real Estate Intelligence")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.filters["tojson"] = json.dumps


@app.exception_handler(auth.RedirectRequired)
async def redirect_required_handler(request: Request, exc: auth.RedirectRequired):
    return RedirectResponse(exc.url, status_code=302)


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def distinct_sources(rows: list[dict]) -> list[dict]:
    """Dedupe (source_name, source_url, retrieved_date) across a set of rows,
    preserving first-seen order, so a chart can cite every source that feeds it
    rather than a hardcoded caption."""
    seen = {}
    for r in rows:
        key = (r.get("source_name"), r.get("source_url"))
        if key not in seen and key[0]:
            seen[key] = {
                "source_name": r["source_name"],
                "source_url": r["source_url"],
                "retrieved_date": r.get("retrieved_date"),
            }
    return list(seen.values())


NAV = [
    ("/", "Overview"),
    ("/areas", "Areas Intelligence"),
    ("/developers", "Developers"),
    ("/demographics", "Buyer Demographics"),
]


def ctx(request: Request, active: str, current_user: dict | None = None, **extra):
    is_admin = bool(
        current_user and auth.ADMIN_EMAIL
        and current_user.get("email", "").lower() == auth.ADMIN_EMAIL.lower()
    )
    return {
        "request": request, "nav": NAV, "active": active,
        "current_user": current_user, "is_admin": is_admin, **extra,
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/"):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "next": next})


@app.get("/auth/login")
async def auth_login(request: Request, next: str = "/"):
    if not next.startswith("/") or next.startswith("//"):
        next = "/"
    request.session["post_login_redirect"] = next
    redirect_uri = f"{PUBLIC_BASE_URL}/auth/callback"
    return await auth.oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await auth.oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]
    request.session["user"] = {
        "sub": userinfo["sub"],
        "email": userinfo.get("email", ""),
        "name": userinfo.get("name", ""),
        "picture": userinfo.get("picture", ""),
    }
    auth.record_login(userinfo)
    next_path = request.session.pop("post_login_redirect", "/")
    return RedirectResponse(next_path, status_code=302)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


@app.get("/admin/stats", response_class=HTMLResponse)
def admin_stats(request: Request, admin: dict = Depends(auth.require_admin)):
    users = auth.query_users()
    total_logins = sum(u["login_count"] for u in users)
    page_view_counts = auth.query_page_view_counts()
    recent_views = auth.query_recent_page_views(50)
    return templates.TemplateResponse(
        "admin_stats.html",
        ctx(
            request, "/admin/stats", current_user=admin,
            users=users, total_logins=total_logins,
            page_view_counts=page_view_counts, recent_views=recent_views,
        ),
    )


@app.get("/api/areas-chart")
def api_areas_chart(user: dict = Depends(auth.require_login_api)):
    return query(
        "SELECT name, price_sqft_low, price_sqft_high FROM areas "
        "WHERE price_sqft_low IS NOT NULL ORDER BY price_sqft_high DESC"
    )


@app.get("/api/developers-chart")
def api_developers_chart(user: dict = Depends(auth.require_login_api)):
    return query(
        "SELECT name, sales_value_aed_bn FROM developers "
        "WHERE sales_value_aed_bn IS NOT NULL ORDER BY sales_value_aed_bn DESC LIMIT 6"
    )


@app.get("/api/nationalities-chart")
def api_nationalities_chart(user: dict = Depends(auth.require_login_api)):
    return query("SELECT nationality, market_share_pct FROM buyer_nationalities ORDER BY rank ASC")


@app.get("/", response_class=HTMLResponse)
def overview(request: Request, user: dict = Depends(auth.require_login)):
    auth.record_page_view(user["email"], request.url.path)
    kpis = query("SELECT * FROM market_kpis ORDER BY id")
    top_areas = query(
        "SELECT * FROM areas WHERE yoy_price_growth_pct IS NOT NULL "
        "ORDER BY yoy_price_growth_pct DESC LIMIT 5"
    )
    top_developers = query(
        "SELECT * FROM developers ORDER BY sales_value_aed_bn DESC LIMIT 5"
    )
    price_range_rows = query("SELECT * FROM areas WHERE price_sqft_low IS NOT NULL")
    developer_chart_rows = query(
        "SELECT * FROM developers WHERE sales_value_aed_bn IS NOT NULL ORDER BY sales_value_aed_bn DESC LIMIT 6"
    )
    return templates.TemplateResponse(
        "overview.html",
        ctx(
            request, "/", current_user=user,
            kpis=kpis, top_areas=top_areas, top_developers=top_developers,
            price_range_sources=distinct_sources(price_range_rows),
            developer_chart_sources=distinct_sources(developer_chart_rows),
        ),
    )


@app.get("/areas", response_class=HTMLResponse)
def areas(
    request: Request,
    user: dict = Depends(auth.require_login),
    sort: str = Query("yoy_price_growth_pct"),
    direction: str = Query("desc"),
    momentum: str = Query("all"),
):
    auth.record_page_view(user["email"], request.url.path)
    sortable = {
        "name": "name",
        "price_sqft_low": "price_sqft_low",
        "rental_yield_high": "rental_yield_high",
        "yoy_price_growth_pct": "yoy_price_growth_pct",
    }
    sort_col = sortable.get(sort, "yoy_price_growth_pct")
    order = "ASC" if direction == "asc" else "DESC"
    where = ""
    params: tuple = ()
    if momentum != "all":
        where = "WHERE momentum_label = ?"
        params = (momentum,)
    rows = query(
        f"SELECT * FROM areas {where} ORDER BY {sort_col} IS NULL, {sort_col} {order}",
        params,
    )
    momentum_options = [r["momentum_label"] for r in query("SELECT DISTINCT momentum_label FROM areas")]
    return templates.TemplateResponse(
        "areas.html",
        ctx(request, "/areas", current_user=user, areas=rows, sort=sort, direction=direction,
            momentum=momentum, momentum_options=momentum_options),
    )


@app.get("/developers", response_class=HTMLResponse)
def developers(
    request: Request,
    user: dict = Depends(auth.require_login),
    sort: str = Query("sales_value_aed_bn"),
    direction: str = Query("desc"),
):
    auth.record_page_view(user["email"], request.url.path)
    sortable = {
        "name": "name",
        "sales_value_aed_bn": "sales_value_aed_bn",
        "on_time_delivery_pct": "on_time_delivery_pct",
        "rera_score": "rera_score",
    }
    sort_col = sortable.get(sort, "sales_value_aed_bn")
    order = "ASC" if direction == "asc" else "DESC"
    rows = query(f"SELECT * FROM developers ORDER BY {sort_col} IS NULL, {sort_col} {order}")
    return templates.TemplateResponse(
        "developers.html",
        ctx(request, "/developers", current_user=user, developers=rows, sort=sort, direction=direction),
    )


@app.get("/demographics", response_class=HTMLResponse)
def demographics(request: Request, user: dict = Depends(auth.require_login)):
    auth.record_page_view(user["email"], request.url.path)
    nationalities = query("SELECT * FROM buyer_nationalities ORDER BY rank ASC")
    brokerages = query("SELECT * FROM brokerages ORDER BY score DESC NULLS LAST, name ASC")
    return templates.TemplateResponse(
        "demographics.html",
        ctx(
            request, "/demographics", current_user=user,
            nationalities=nationalities, brokerages=brokerages,
            nationality_sources=distinct_sources(nationalities),
        ),
    )
