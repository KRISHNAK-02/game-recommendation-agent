"""RAWG API Client Wrapper for querying video game data."""

import os
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()


class RAWGClient:
    """Client for interacting with the RAWG Video Games Database API."""

    BASE_URL = "https://api.rawg.io/api"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RAWG_API_KEY")
        if not self.api_key:
            raise ValueError(
                "RAWG API key not found. Please set RAWG_API_KEY in your .env file or environment variables."
            )

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Internal helper to execute GET requests against RAWG API."""
        if params is None:
            params = {}
        params["key"] = self.api_key

        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        try:
            response = requests.get(url, params=params, timeout=12)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise RuntimeError("Invalid RAWG API key. Please verify your API key in .env.") from e
            elif response.status_code == 404:
                return {"error": "Resource not found", "results": []}
            raise RuntimeError(f"RAWG API request failed: {e}") from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error communicating with RAWG API: {e}") from e

    def search_games(
        self,
        query: str,
        page_size: int = 8,
        ordering: Optional[str] = None,
        search_precise: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search for games matching a text query with relevance ranking."""
        params: Dict[str, Any] = {
            "search": query,
            "page_size": page_size,
            "search_precise": str(search_precise).lower(),
        }
        if ordering:
            params["ordering"] = ordering

        data = self._get("games", params=params)
        return data.get("results", [])

    def get_game_details(self, game_id_or_slug: str | int) -> Dict[str, Any]:
        """Fetch full details for a specific game."""
        return self._get(f"games/{game_id_or_slug}")

    def filter_games(
        self,
        genres: Optional[str] = None,
        platforms: Optional[str] = None,
        tags: Optional[str] = None,
        dates: Optional[str] = None,
        metacritic: Optional[str] = None,
        ordering: str = "-added",
        page_size: int = 8,
    ) -> List[Dict[str, Any]]:
        """Filter games by genre, platform, tags, release date range, or metacritic score."""
        params: Dict[str, Any] = {
            "page_size": page_size,
            "ordering": ordering,
        }
        if genres:
            params["genres"] = genres
        if platforms:
            params["platforms"] = platforms
        if tags:
            params["tags"] = tags
        if dates:
            params["dates"] = dates
        if metacritic:
            params["metacritic"] = metacritic

        data = self._get("games", params=params)
        return data.get("results", [])

    def get_similar_games(self, game_slug_or_id: str | int, page_size: int = 6) -> List[Dict[str, Any]]:
        """Find games similar in genre, gameplay, and popularity to a given game."""
        details = self.get_game_details(game_slug_or_id)
        if "error" in details:
            return []

        current_id = details.get("id")

        # 1. Check game series / sequels / prequels
        data = self._get(f"games/{game_slug_or_id}/game-series", params={"page_size": page_size})
        series_results = [g for g in data.get("results", []) if g.get("id") != current_id]
        if len(series_results) >= 4:
            return series_results[:page_size]

        # 2. Match by genres & tags sorted by popularity/player count (-added)
        genre_slugs = [g["slug"] for g in details.get("genres", [])[:2]]
        tag_slugs = [t["slug"] for t in details.get("tags", [])[:2]]

        genres_param = ",".join(genre_slugs) if genre_slugs else None
        tags_param = ",".join(tag_slugs) if tag_slugs else None

        filtered = self.filter_games(
            genres=genres_param,
            tags=tags_param,
            ordering="-added",
            page_size=page_size + 4,
        )

        similar = [g for g in filtered if g.get("id") != current_id][:page_size]
        # Combine series and genre matches
        combined = []
        seen = set()
        for g in series_results + similar:
            if g.get("id") and g["id"] not in seen and g["id"] != current_id:
                seen.add(g["id"])
                combined.append(g)

        return combined[:page_size] if combined else series_results

    def get_top_rated_games(self, page_size: int = 8, dates: str = "2020-01-01,2026-12-31") -> List[Dict[str, Any]]:
        """Get highest rated recent games."""
        params = {
            "dates": dates,
            "ordering": "-metacritic",
            "page_size": page_size,
            "metacritic": "80,100",
        }
        data = self._get("games", params=params)
        return data.get("results", [])

    def get_popular_genres(self) -> List[Dict[str, Any]]:
        """Get list of popular genres."""
        data = self._get("genres", params={"page_size": 20})
        return data.get("results", [])
