import base64
import re
import time
from typing import Optional, List, Tuple

import httpx

from ..utils import _env_any, _trim_outliers_and_median

_EBAY_TOKEN_CACHE = {"token": None, "expires_at": 0.0}

# Listings whose titles contain these words are almost certainly NOT
# a single loose game and should be excluded from median calculations.
_BUNDLE_KEYWORDS = {
    "bundle", "lot", "sammlung", "konvolut", "paket", "set of",
    "collection", "wholesale", "bulk", "joblot", "job lot",
    "console", "konsole", "system", "hardware",
    "controller", "zubehör", "accessory", "accessories",
    "defekt", "defective", "broken", "not working", "für bastler",
    "ersatzteile", "parts only", "as is",
}


def _ebay_credentials():
    client_id = _env_any("EBAY_CLIENT_ID", "EBAY_APP_ID", "EBAY_APPID", "EBAY_CLIENTID")
    client_secret = _env_any("EBAY_CLIENT_SECRET", "EBAY_SECRET", "EBAY_CLIENTSECRET", "EBAY_SECRET_KEY")
    if not client_id or not client_secret:
        return None, None
    return client_id, client_secret


def _normalise(text: str) -> str:
    """Lowercase and collapse whitespace for fuzzy matching."""
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def _title_is_relevant(item_title: str, game_title: str, platform_name: str) -> bool:
    """Return True if the eBay listing looks like a single copy of
    the requested game, not a bundle / console / accessory / defect."""
    norm_item = _normalise(item_title)
    norm_game = _normalise(game_title)

    # ── Reject listings that contain bundle / defect keywords ──
    for kw in _BUNDLE_KEYWORDS:
        if kw in norm_item:
            return False

    # ── Reject listings with "x Spiele" or "x games" patterns ──
    if re.search(r"\d+\s*(spiele|games|titles|stück|stk)", norm_item):
        return False

    # ── Require that the listing title contains the core game words ──
    # Extract the significant words from the game title (≥ 3 chars)
    game_words = [w for w in norm_game.split() if len(w) >= 3]
    if not game_words:
        return True  # very short title, can't filter meaningfully

    # At least half of the game title's significant words should appear
    matches = sum(1 for w in game_words if w in norm_item)
    if matches < max(1, len(game_words) * 0.5):
        return False

    return True


async def get_ebay_token() -> Optional[str]:
    client_id, client_secret = _ebay_credentials()
    if not client_id or not client_secret:
        return None

    now = time.time()
    cached = _EBAY_TOKEN_CACHE.get("token")
    if cached and _EBAY_TOKEN_CACHE.get("expires_at", 0) > now:
        return cached

    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    body = "grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope"

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            res = await client.post("https://api.ebay.com/identity/v1/oauth2/token", headers=headers, content=body)
        if res.status_code >= 400:
            print(f"eBay token error ({res.status_code}): {res.text[:500]}")
            return None

        data = res.json()
        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 0))
        if not token:
            return None

        _EBAY_TOKEN_CACHE["token"] = token
        _EBAY_TOKEN_CACHE["expires_at"] = now + max(expires_in - 60, 60)
        return token
    except Exception as e:
        print(f"eBay token fetch error: {e}")
        return None


async def fetch_ebay_market_price(title: str, platform_name: str):
    token = await get_ebay_token()
    if not token:
        return None

    query = " ".join(part for part in [title, platform_name] if part).strip()
    params = {"q": query, "filter": "conditionIds:{2750|3000}", "limit": "50"}
    headers = {"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"}

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            res = await client.get("https://api.ebay.com/buy/browse/v1/item_summary/search", params=params, headers=headers)

        if res.status_code >= 400:
            print(f"eBay browse error ({res.status_code}): {res.text[:500]}")
            return None

        payload = res.json()
        items = payload.get("itemSummaries", []) or []

        prices: List[float] = []
        skipped = 0
        for item in items:
            item_title = item.get("title", "")

            # ── Skip irrelevant listings (bundles, consoles, etc.) ──
            if not _title_is_relevant(item_title, title, platform_name):
                skipped += 1
                continue

            value = (item.get("price") or {}).get("value")
            if value is None:
                continue
            try:
                price = float(value)
            except (TypeError, ValueError):
                continue
            if price > 0:
                prices.append(price)

        if skipped:
            print(f"eBay: filtered out {skipped} irrelevant listings for '{query}'")

        median_price, trimmed, min_price, max_price = _trim_outliers_and_median(prices)
        if median_price is None:
            return None

        return {
            "market_price": round(median_price, 2),
            "sample_size": len(trimmed),
            "price_min": round(min_price, 2),
            "price_max": round(max_price, 2),
        }
    except Exception as e:
        print(f"eBay browse error for '{query}': {e}")
        return None
