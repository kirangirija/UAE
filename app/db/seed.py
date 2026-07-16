"""
Seeds uae_re.db with curated Tier 2 data gathered from public real estate
market reports (July 2026). Every row cites its source and retrieval date
so the UI can show provenance. This is a manually-researched snapshot for
the Phase 1 MVP; Phase 2 replaces the manual step with a scheduled
Perplexity (via OpenRouter) research agent, and live DLD/Dubai Pulse
transaction data (Tier 1) will supersede the market_kpis estimates here
once API credentials are granted.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "uae_re.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

RETRIEVED = "2026-07-16"

MARKET_KPIS = [
    ("Full-year transaction value", 917, "AED bn", "2025 (Full Year)", 20.0,
     "270,000+ transactions recorded across the year",
     "Dubai Public Debt Management Office",
     "https://dmo.dof.gov.ae/en/news-and-publications/latest-press-releases/dubai-s-real-estate-market-records-new-historic-milestone-with-transactions-exceeding-aed917-billion-usd-2497-bn-in-2025/"),
    ("Total transaction value", 252, "AED bn", "Q1 2026", 31.0,
     "Volume up 6% YoY over the same period",
     "Dubai Land Department",
     "https://dubailand.gov.ae/en/news-media/dubai-s-real-estate-transactions-surge-31-to-reach-aed-252-billion-in-q1-2026/"),
    ("Residential transaction value", 137.31, "AED bn", "Q1 2026", None,
     "45,221 residential transactions",
     "Market report aggregation",
     "https://haus51.com/dubai-property-market-2026-record-sales-investment"),
    ("Residential transaction value", 221.4, "AED bn", "H1 2026", None,
     "79,281 residential sales",
     "Market report aggregation",
     "https://www.engelvoelkers.com/ae/en/resources/dubai-housing-market"),
    ("Off-plan share of transaction value", 75.5, "%", "2026", None,
     "Up from ~55% in 2022; range reported 73-78%",
     "TruHauz / Gulf Business market coverage",
     "https://gulfbusiness.com/en/2026/real-estate/dubai-property-market-may-2026-transactions-investor-hotspots/"),
    ("Total investment value", 173, "AED bn", "2026 (YTD)", None,
     "AED 148.35bn international + AED 32bn from women investors; new participants up 14%",
     "Gulf Business",
     "https://gulfbusiness.com/en/2026/real-estate/dubai-property-market-may-2026-transactions-investor-hotspots/"),
    ("Total transactions", 42800, "count", "Q1 2026", 18.0,
     "All transaction types (broader methodology than DLD's headline figure)",
     "Brokerage industry ranking report",
     "https://realestateclubdubai.com/business-directory/real-estate-agencies/rankings-2026"),
]

DEVELOPERS = [
    ("Emaar Properties", 65.8, "2025 Full Year", "8,000+", "2020-2024", 92, 97,
     "Recommended for delivery certainty and resale liquidity; market leader by sales value",
     "Dubai developer ranking reports", "https://timehomesrealestate.com/news/dubai-top-developers-by-sales-and-volume-q1-2026-ranking-report"),
    ("DAMAC Properties", 35.9, "2025 Full Year", "50,000+ (since 2002)", "2002-2026", 82, 94,
     "High volume, lifestyle-branded developments; 54,000+ units under construction",
     "Dubai developer ranking reports", "https://timehomesrealestate.com/news/dubai-top-developers-by-sales-and-volume-q1-2026-ranking-report"),
    ("Sobha Realty", 30.0, "2025 Full Year", "6,000+", "2020-2024", 90, None,
     "Recommended for delivery certainty and resale liquidity",
     "Dubai developer ranking reports", "https://timehomesrealestate.com/news/dubai-top-developers-by-sales-and-volume-q1-2026-ranking-report"),
    ("Binghatti", 26.0, "2025 Full Year", None, None, None, None,
     "High-volume, fast-growing developer; lifestyle differentiation positioning",
     "Dubai developer ranking reports", "https://timehomesrealestate.com/news/dubai-top-developers-by-sales-and-volume-q1-2026-ranking-report"),
    ("Meraas", 7.73, "Q1 2026", None, None, None, None,
     "Ultra-premium lifestyle positioning; only 1,048 transactions but high average value",
     "Dubai developer ranking reports", "https://timehomesrealestate.com/news/dubai-top-developers-by-sales-and-volume-q1-2026-ranking-report"),
    ("Nakheel", 7.27, "Q1 2026", None, None, 88, 90,
     "Palm Jumeirah developer; ultra-premium lifestyle appreciation positioning",
     "Dubai developer ranking reports", "https://timehomesrealestate.com/news/dubai-top-developers-by-sales-and-volume-q1-2026-ranking-report"),
]

AREAS = [
    ("Dubai Marina", 1600, 2400, 6, 7, None, "Established / Stable",
     "Waterfront residential", "High-liquidity secondary market",
     "Sherwoods Property investment guide", "https://sherwoodsproperty.com/best-areas-to-invest-in-dubai-in-2026-high-roi-locations/"),
    ("Downtown Dubai", 2500, 3500, None, None, None, "Established / Premium",
     "Luxury residential", "Commands premium pricing for luxury positioning",
     "Sherwoods Property investment guide", "https://sherwoodsproperty.com/best-areas-to-invest-in-dubai-in-2026-high-roi-locations/"),
    ("Business Bay", 1400, 2000, 6, 7, None, "Established / Growing",
     "Mixed residential & commercial", "Strong rental demand near DIFC/downtown core",
     "Sherwoods Property investment guide", "https://sherwoodsproperty.com/best-areas-to-invest-in-dubai-in-2026-high-roi-locations/"),
    ("Jumeirah Village Circle (JVC)", 900, 1300, 7, 8, None, "Booming",
     "Affordable residential", "Highest rental yields of the tracked areas; most affordable entry point",
     "Sherwoods Property investment guide", "https://sherwoodsproperty.com/best-areas-to-invest-in-dubai-in-2026-high-roi-locations/"),
    ("Dubai Hills Estate", None, None, None, None, None, "Established / Growing",
     "Family villas & townhouses", "Consistent family-focused rental demand",
     "Sherwoods Property investment guide", "https://sherwoodsproperty.com/best-areas-to-invest-in-dubai-in-2026-high-roi-locations/"),
    ("Dubai Islands", None, None, None, None, 50.8, "Booming",
     "Waterfront off-plan", "Strongest YoY price growth of any tracked corridor in early 2026",
     "Market trend report", "https://sherwoodsproperty.com/dubai-next-investment-hotspots-2026/"),
]

NATIONALITIES = [
    ("India", 20.6, 1), ("United Kingdom", 13.3, 2), ("Egypt", 12.6, 3),
    ("United States", 9.0, 4), ("Pakistan", 6.9, 5), ("Saudi Arabia", 5.7, 6),
    ("Australia", 5.7, 7), ("Germany", 4.2, 8), ("France", 3.8, 9),
    ("Canada", 3.0, 10), ("Netherlands", 2.83, 11), ("Russia", 2.5, 12),
    ("Morocco", 2.33, 13), ("Spain", 2.11, 14), ("Kuwait", 2.11, 15),
    ("Turkey", 2.05, 16), ("Nigeria", 1.89, 17),
]
NAT_SOURCE = ("Khaleej Times", "https://www.khaleejtimes.com/business/indian-uk-egyptian-investors-top-dubai-property-buyers-in-2026")
NAT_PERIOD = "Early 2026"

BROKERAGES = [
    ("Betterhomes", 1986, "97", "400-500", "Gold", "Deepest operational base: 8,500+ managed properties, UAE-wide coverage across 10+ communities", 89.48,
     "Real estate agency ranking report", "https://realestateclubdubai.com/business-directory/real-estate-agencies/rankings-2026"),
    ("Allsopp & Allsopp", 2008, "1815", "700+", None, "First ISO-certified Dubai agency (2009); largest agent headcount in the peer set", None,
     "Real estate agency ranking report", "https://realestateclubdubai.com/business-directory/real-estate-agencies/rankings-2026"),
    ("Provident Estate", None, None, None, "Gold", "Strongest evidenced strength in developer-channel (off-plan) volume", 89.48,
     "Real estate agency ranking report", "https://realestateclubdubai.com/business-directory/real-estate-agencies/rankings-2026"),
]


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    conn.executemany(
        """INSERT INTO market_kpis
           (metric_name, value, unit, period_label, yoy_change_pct, note, source_name, source_url, retrieved_date)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [row + (RETRIEVED,) for row in MARKET_KPIS],
    )
    conn.executemany(
        """INSERT INTO developers
           (name, sales_value_aed_bn, sales_value_period, units_delivered, units_delivered_period,
            on_time_delivery_pct, rera_score, positioning_note, source_name, source_url, retrieved_date)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [row + (RETRIEVED,) for row in DEVELOPERS],
    )
    conn.executemany(
        """INSERT INTO areas
           (name, price_sqft_low, price_sqft_high, rental_yield_low, rental_yield_high,
            yoy_price_growth_pct, momentum_label, project_type_focus, notes, source_name, source_url, retrieved_date)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        [row + (RETRIEVED,) for row in AREAS],
    )
    conn.executemany(
        """INSERT INTO buyer_nationalities
           (nationality, market_share_pct, period_label, rank, source_name, source_url, retrieved_date)
           VALUES (?,?,?,?,?,?,?)""",
        [(n, pct, NAT_PERIOD, rank, NAT_SOURCE[0], NAT_SOURCE[1], RETRIEVED) for n, pct, rank in NATIONALITIES],
    )
    conn.executemany(
        """INSERT INTO brokerages
           (name, founded_year, orn, agent_count, dld_tier, specialty_note, score, source_name, source_url, retrieved_date)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        [row + (RETRIEVED,) for row in BROKERAGES],
    )

    conn.commit()
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ["market_kpis", "developers", "areas", "buyer_nationalities", "brokerages"]}
    conn.close()
    print(f"Seeded {DB_PATH}: {counts}")


if __name__ == "__main__":
    main()
