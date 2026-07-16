import json
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "db" / "uae_re.db"

app = FastAPI(title="UAE Real Estate Intelligence")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.filters["tojson"] = json.dumps


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


def ctx(request: Request, active: str, **extra):
    return {"request": request, "nav": NAV, "active": active, **extra}


@app.get("/api/areas-chart")
def api_areas_chart():
    return query(
        "SELECT name, price_sqft_low, price_sqft_high FROM areas "
        "WHERE price_sqft_low IS NOT NULL ORDER BY price_sqft_high DESC"
    )


@app.get("/api/developers-chart")
def api_developers_chart():
    return query(
        "SELECT name, sales_value_aed_bn FROM developers "
        "WHERE sales_value_aed_bn IS NOT NULL ORDER BY sales_value_aed_bn DESC LIMIT 6"
    )


@app.get("/api/nationalities-chart")
def api_nationalities_chart():
    return query("SELECT nationality, market_share_pct FROM buyer_nationalities ORDER BY rank ASC")


@app.get("/", response_class=HTMLResponse)
def overview(request: Request):
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
            request, "/",
            kpis=kpis, top_areas=top_areas, top_developers=top_developers,
            price_range_sources=distinct_sources(price_range_rows),
            developer_chart_sources=distinct_sources(developer_chart_rows),
        ),
    )


@app.get("/areas", response_class=HTMLResponse)
def areas(
    request: Request,
    sort: str = Query("yoy_price_growth_pct"),
    direction: str = Query("desc"),
    momentum: str = Query("all"),
):
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
        ctx(request, "/areas", areas=rows, sort=sort, direction=direction,
            momentum=momentum, momentum_options=momentum_options),
    )


@app.get("/developers", response_class=HTMLResponse)
def developers(
    request: Request,
    sort: str = Query("sales_value_aed_bn"),
    direction: str = Query("desc"),
):
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
        "developers.html", ctx(request, "/developers", developers=rows, sort=sort, direction=direction)
    )


@app.get("/demographics", response_class=HTMLResponse)
def demographics(request: Request):
    nationalities = query("SELECT * FROM buyer_nationalities ORDER BY rank ASC")
    brokerages = query("SELECT * FROM brokerages ORDER BY score DESC NULLS LAST, name ASC")
    return templates.TemplateResponse(
        "demographics.html",
        ctx(
            request, "/demographics",
            nationalities=nationalities, brokerages=brokerages,
            nationality_sources=distinct_sources(nationalities),
        ),
    )
