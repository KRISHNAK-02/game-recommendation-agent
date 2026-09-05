"""Agent module providing AI reasoning and game recommendation logic."""

import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from rawg_client import RAWGClient
from deals_client import DealsClient

load_dotenv()


class GameRecommendationAgent:
    """Intelligent agent that handles game recommendations using RAWG API, CheapShark deals, and AI reasoning."""

    def __init__(self, rawg_client: RAWGClient, gemini_api_key: Optional[str] = None):
        self.rawg = rawg_client
        self.deals_client = DealsClient()
        self.gemini_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.ai_available = False
        self._init_ai()

    def _init_ai(self):
        """Attempt to initialize Gemini client if key is configured."""
        if not self.gemini_key or self.gemini_key.strip() == "" or "your_" in self.gemini_key:
            self.ai_available = False
            return

        try:
            from google import genai
            self.genai_client = genai.Client(api_key=self.gemini_key)
            self.ai_available = True
        except Exception:
            self.ai_available = False

    def attach_deals_to_games(self, games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetch and attach best available live deal to each game."""
        for g in games:
            name = g.get("name", "")
            if name:
                deal = self.deals_client.get_best_deal_for_game(name)
                if deal:
                    g["best_deal"] = deal
        return games

    def recommend_by_query(self, query: str) -> Dict[str, Any]:
        """Recommend games based on natural language user request."""
        if self.ai_available:
            result = self._recommend_with_ai(query)
        else:
            result = self._recommend_with_heuristics(query)

        if result.get("games"):
            result["games"] = self.attach_deals_to_games(result["games"])
        return result

    def _recommend_with_ai(self, query: str) -> Dict[str, Any]:
        """Use Gemini to interpret user taste, search RAWG, and formulate customized recommendations."""
        search_results = self.rawg.search_games(query, page_size=8)
        
        query_lower = query.lower()
        genre_matches = []
        known_genres = ["action", "rpg", "adventure", "shooter", "indie", "strategy", "puzzle", "simulation", "platformer", "racing", "sports", "horror"]
        for g in known_genres:
            if g in query_lower:
                genre_matches.append(g)
        
        filtered_results = []
        if genre_matches:
            filtered_results = self.rawg.filter_games(genres=",".join(genre_matches), page_size=6)

        combined_candidates = []
        seen_ids = set()
        for g in search_results + filtered_results:
            if g.get("id") and g["id"] not in seen_ids:
                seen_ids.add(g["id"])
                combined_candidates.append(g)

        if not combined_candidates:
            combined_candidates = self.rawg.get_top_rated_games(page_size=6)

        candidates_summary = []
        for g in combined_candidates[:8]:
            p_names = [p.get("platform", {}).get("name", "") for p in g.get("platforms", []) if p.get("platform")]
            g_names = [gn.get("name", "") for gn in g.get("genres", [])]
            candidates_summary.append({
                "id": g.get("id"),
                "name": g.get("name"),
                "rating": g.get("rating"),
                "metacritic": g.get("metacritic"),
                "platforms": p_names[:4],
                "genres": g_names[:3],
                "slug": g.get("slug")
            })

        system_instruction = (
            "You are Nexus, an enthusiastic, expert video game recommendation advisor. "
            "Given the user's request and candidate games fetched from the database, "
            "analyze and pick the 3 to 5 best matching games. "
            "For each picked game, write a compelling 1-2 sentence rationale explaining exactly why they will love it based on their request. "
            "Conclude with a brief gamer tip."
        )

        prompt = f"""
User Query: "{query}"

Available Database Game Candidates:
{candidates_summary}

Please provide your recommendations in a friendly, engaging markdown format.
"""
        try:
            response = self.genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"system_instruction": system_instruction}
            )
            return {
                "success": True,
                "ai_text": response.text,
                "games": combined_candidates[:5],
                "mode": "ai"
            }
        except Exception as e:
            res = self._recommend_with_heuristics(query)
            res["error_note"] = f"AI reasoning unavailable ({e}), using direct database match."
            return res

    def _recommend_with_heuristics(self, query: str) -> Dict[str, Any]:
        """Smart rule-based matcher when AI API key is not configured."""
        query_lower = query.lower()

        # Check for similar game indicators
        for marker in ["like ", "similar to ", "after ", "resemble "]:
            if marker in query_lower:
                game_target = query_lower.split(marker)[1].strip().split(" ")[0:3]
                target_str = " ".join(game_target).strip(" ,.?")
                if target_str:
                    search = self.rawg.search_games(target_str, page_size=2)
                    if search:
                        similar = self.rawg.get_similar_games(search[0]["id"], page_size=5)
                        if similar:
                            return {
                                "success": True,
                                "games": similar,
                                "summary": f"Found games similar in mechanics and atmosphere to '{search[0].get('name')}'",
                                "mode": "heuristic"
                            }

        # Check genres
        known_genres = {
            "rpg": "role-playing-games-rpg",
            "role playing": "role-playing-games-rpg",
            "action": "action",
            "adventure": "adventure",
            "shooter": "shooter",
            "fps": "shooter",
            "strategy": "strategy",
            "puzzle": "puzzle",
            "indie": "indie",
            "horror": "action,adventure",
            "cozy": "indie,simulation",
            "simulation": "simulation",
            "racing": "racing",
            "sports": "sports",
            "platformer": "platformer",
        }

        matched_genres = []
        for word, slug in known_genres.items():
            if word in query_lower:
                matched_genres.append(slug)

        if matched_genres:
            genre_param = ",".join(matched_genres)
            games = self.rawg.filter_games(genres=genre_param, ordering="-rating", page_size=6)
            if games:
                return {
                    "success": True,
                    "games": games,
                    "summary": f"Top rated games matching genres: {', '.join(matched_genres)}",
                    "mode": "heuristic"
                }

        games = self.rawg.search_games(query, page_size=6)
        if not games:
            games = self.rawg.get_top_rated_games(page_size=6)

        return {
            "success": True,
            "games": games,
            "summary": f"Best matching games for '{query}'",
            "mode": "heuristic"
        }

    def get_similar(self, game_name_or_slug: str) -> Dict[str, Any]:
        """Find games similar to a specific title."""
        search = self.rawg.search_games(game_name_or_slug, page_size=6)
        if not search:
            return {"success": False, "error": f"Game '{game_name_or_slug}' not found."}

        # Pick the most popular/flagship game among top matches (e.g. God of War 2018 over God of War I)
        target_game = max(search[:3], key=lambda x: x.get("added", 0)) if len(search) > 1 else search[0]

        # Fetch complete details & deal for the searched game
        details = self.rawg.get_game_details(target_game["id"])
        if "error" not in details:
            target_game = details

        target_deal = self.deals_client.get_best_deal_for_game(target_game.get("name", ""))
        if target_deal:
            target_game["best_deal"] = target_deal

        similar_games = self.rawg.get_similar_games(target_game["id"], page_size=6)
        similar_games = self.attach_deals_to_games(similar_games)
        return {
            "success": True,
            "target_game": target_game,
            "similar_games": similar_games
        }

    def recommend_squad_coop(self, player1_taste: str, player2_taste: str) -> Dict[str, Any]:
        """Find co-op / multiplayer games that satisfy two distinct player tastes."""
        # Query co-op tagged games with high ratings
        coop_tags = "co-op,multiplayer,cooperative,local-co-op"
        
        # 1. Search candidates with co-op tags from RAWG
        candidates = self.rawg.filter_games(tags=coop_tags, ordering="-metacritic", page_size=12)
        if not candidates:
            candidates = self.rawg.search_games(f"{player1_taste} {player2_taste} co-op", page_size=8)

        if self.ai_available:
            summary_list = []
            for g in candidates[:8]:
                summary_list.append({
                    "name": g.get("name"),
                    "metacritic": g.get("metacritic"),
                    "genres": [gn.get("name", "") for gn in g.get("genres", [])],
                    "slug": g.get("slug")
                })
            
            prompt = f"""
Two friends want to play a co-op/multiplayer video game together:
- Player 1 preference: "{player1_taste}"
- Player 2 preference: "{player2_taste}"

Available candidate co-op games:
{summary_list}

Select the 3 best multiplayer/co-op games that act as the perfect middle ground / compromise between both players.
For each game, explain what Player 1 will love and what Player 2 will love about it.
"""
            try:
                resp = self.genai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                chosen_games = self.attach_deals_to_games(candidates[:5])
                return {
                    "success": True,
                    "ai_text": resp.text,
                    "games": chosen_games,
                    "mode": "ai"
                }
            except Exception:
                pass

        # Heuristic fallback for squad matchmaking
        chosen = self.attach_deals_to_games(candidates[:5])
        return {
            "success": True,
            "summary": f"Top rated co-op games bringing together '{player1_taste}' & '{player2_taste}'",
            "games": chosen,
            "mode": "heuristic"
        }

    def wizard_recommend(
        self,
        genre: Optional[str] = None,
        platform_id: Optional[str] = None,
        min_metacritic: Optional[int] = None,
        era: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Filter games based on guided wizard criteria."""
        dates = None
        if era == "modern":
            dates = "2020-01-01,2026-12-31"
        elif era == "golden":
            dates = "2010-01-01,2019-12-31"
        elif era == "classic":
            dates = "1990-01-01,2009-12-31"

        meta_param = f"{min_metacritic},100" if min_metacritic else "70,100"

        games = self.rawg.filter_games(
            genres=genre,
            platforms=platform_id,
            dates=dates,
            metacritic=meta_param,
            ordering="-metacritic",
            page_size=6
        )
        return self.attach_deals_to_games(games)
