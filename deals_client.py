"""CheapShark API Client for fetching real-time video game prices, discounts, and store deals."""

from typing import Any, Dict, List, Optional
import requests

STORES_MAP = {
    "1": "Steam",
    "2": "GamersGate",
    "3": "GreenManGaming",
    "6": "Direct2Drive",
    "7": "GOG",
    "8": "Origin",
    "11": "Humble Store",
    "13": "Uplay",
    "15": "Fanatical",
    "21": "WinGameStore",
    "23": "GameBillet",
    "24": "Voidu",
    "25": "Epic Games Store",
    "27": "Gamesplanet",
    "28": "Gamesload",
    "29": "2Game",
    "30": "IndieGala",
    "31": "Blizzard Shop",
    "32": "AllYouPlay",
    "33": "DLGamer",
    "34": "Noctre",
}

DEFAULT_HEADERS = {
    "User-Agent": "GameRecommendationAgent/1.0 (https://github.com/game-recommendation-agent)",
    "Accept": "application/json",
}


class DealsClient:
    """Client for fetching live PC game discounts and prices from CheapShark API."""

    BASE_URL = "https://www.cheapshark.com/api/1.0"

    def __init__(self):
        self.stores_cache = STORES_MAP

    def search_deals(self, title: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for live deals matching game title across authorized PC digital stores."""
        url = f"{self.BASE_URL}/deals"
        params = {
            "title": title,
            "pageSize": limit,
            "sortBy": "Savings",
        }
        try:
            resp = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=8)
            resp.raise_for_status()
            deals = resp.json()
            if not isinstance(deals, list):
                return []
            
            enhanced_deals = []
            for d in deals:
                store_id = str(d.get("storeID", ""))
                store_name = self.stores_cache.get(store_id, f"Store #{store_id}")
                
                try:
                    normal_price = float(d.get("normalPrice", 0.0))
                except (ValueError, TypeError):
                    normal_price = 0.0

                try:
                    sale_price = float(d.get("salePrice", 0.0))
                except (ValueError, TypeError):
                    sale_price = 0.0

                try:
                    savings = float(d.get("savings", 0.0))
                except (ValueError, TypeError):
                    savings = 0.0

                deal_id = d.get("dealID", "")
                deal_link = f"https://www.cheapshark.com/redirect?dealID={deal_id}" if deal_id else ""

                enhanced_deals.append({
                    "title": d.get("title", title),
                    "store": store_name,
                    "sale_price": sale_price,
                    "normal_price": normal_price,
                    "savings_percent": round(savings, 0),
                    "is_on_sale": savings > 0.0,
                    "deal_rating": d.get("dealRating", "0"),
                    "metacritic": d.get("metacriticScore"),
                    "deal_url": deal_link,
                    "steam_app_id": d.get("steamAppID"),
                })
            return enhanced_deals
        except Exception:
            return []

    def get_best_deal_for_game(self, title: str) -> Optional[Dict[str, Any]]:
        """Find the single lowest price/best deal currently available for a game."""
        # Clean title for better matching (strip colons/subtitles if needed)
        clean_title = title.split(":")[0].strip()
        deals = self.search_deals(clean_title, limit=5)
        if not deals:
            return None
        return sorted(deals, key=lambda x: x["sale_price"])[0]
