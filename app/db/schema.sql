-- UAE Real Estate Intelligence Dashboard
-- Tier 2 curated schema: every fact carries its own source citation and retrieval date.

CREATE TABLE IF NOT EXISTS market_kpis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    period_label TEXT NOT NULL,
    yoy_change_pct REAL,
    note TEXT,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    retrieved_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS developers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sales_value_aed_bn REAL,
    sales_value_period TEXT,
    units_delivered TEXT,
    units_delivered_period TEXT,
    on_time_delivery_pct REAL,
    rera_score REAL,
    positioning_note TEXT,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    retrieved_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price_sqft_low REAL,
    price_sqft_high REAL,
    rental_yield_low REAL,
    rental_yield_high REAL,
    yoy_price_growth_pct REAL,
    momentum_label TEXT,
    project_type_focus TEXT,
    notes TEXT,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    retrieved_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS buyer_nationalities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nationality TEXT NOT NULL,
    market_share_pct REAL NOT NULL,
    period_label TEXT NOT NULL,
    rank INTEGER,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    retrieved_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brokerages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    founded_year INTEGER,
    orn TEXT,
    agent_count TEXT,
    dld_tier TEXT,
    specialty_note TEXT,
    score REAL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    retrieved_date TEXT NOT NULL
);
