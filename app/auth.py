"""
Google Sign-In gate + lightweight usage analytics.

Login/usage data lives in Supabase Postgres (users + page_views tables,
public schema), not in the local SQLite file used for curated market data.
That's a deliberate split: Render's free-tier disk is ephemeral and wipes
local files on every redeploy, so anything we want to persist long-term
(login history, usage stats) has to live somewhere durable instead. Access
is via Supabase's REST API (PostgREST) using the anon/publishable key --
see the "backend full access" RLS policies in the create_login_analytics_tables
migration for why that key is allowed to read/write these two tables.
"""
import os

import httpx
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request

load_dotenv()

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
_supabase_headers = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
}

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def record_login(userinfo: dict) -> None:
    try:
        httpx.post(
            f"{SUPABASE_URL}/rest/v1/rpc/record_login",
            headers=_supabase_headers,
            json={
                "p_google_sub": userinfo["sub"],
                "p_email": userinfo.get("email", ""),
                "p_name": userinfo.get("name", ""),
                "p_picture": userinfo.get("picture", ""),
            },
            timeout=10,
        ).raise_for_status()
    except httpx.HTTPError as e:
        print(f"record_login failed (Supabase unreachable?): {e}")


def record_page_view(email: str, path: str) -> None:
    try:
        httpx.post(
            f"{SUPABASE_URL}/rest/v1/page_views",
            headers=_supabase_headers,
            json={"email": email, "path": path},
            timeout=10,
        ).raise_for_status()
    except httpx.HTTPError as e:
        print(f"record_page_view failed (Supabase unreachable?): {e}")


def query_users() -> list[dict]:
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=_supabase_headers,
        params={"select": "*", "order": "last_seen.desc"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def query_page_view_counts() -> list[dict]:
    r = httpx.post(
        f"{SUPABASE_URL}/rest/v1/rpc/page_view_counts",
        headers=_supabase_headers,
        json={},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def query_recent_page_views(limit: int = 50) -> list[dict]:
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/page_views",
        headers=_supabase_headers,
        params={"select": "*", "order": "viewed_at.desc", "limit": str(limit)},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


class RedirectRequired(Exception):
    """Raised by require_login for page routes; main.py maps this to a 302 redirect."""

    def __init__(self, url: str):
        self.url = url


def require_login(request: Request) -> dict:
    """Use on page routes. Redirects the browser to /login if there's no session."""
    user = request.session.get("user")
    if not user:
        raise RedirectRequired(f"/login?next={request.url.path}")
    return user


def require_login_api(request: Request) -> dict:
    """Use on JSON API routes. Returns 401 instead of redirecting (fetch() can't follow a login redirect usefully)."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(user: dict = Depends(require_login)) -> dict:
    if not ADMIN_EMAIL or user.get("email", "").lower() != ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Forbidden")
    return user
