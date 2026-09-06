import os
import sys
from typing import Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.status import Status

from rawg_client import RAWGClient
from agent import GameRecommendationAgent
from deals_client import DealsClient
import art_renderer
import cli_ui as ui

load_dotenv()
console = Console(force_terminal=True)


def ensure_api_keys() -> RAWGClient:
    """Check for RAWG API key, prompt user if missing and save to .env."""
    api_key = os.getenv("RAWG_API_KEY")
    if not api_key or api_key.strip() == "" or "your_" in api_key:
        ui.print_info("No RAWG API key found in .env.")
        console.print("[yellow]You can get a free RAWG key at [bold underline]https://rawg.io/apidocs[/bold underline][/yellow]\n")

        entered_key = Prompt.ask("[bold cyan]Please enter your RAWG API Key[/bold cyan]").strip()
        if not entered_key:
            ui.print_error("RAWG API key is required to fetch game data. Exiting.")
            sys.exit(1)

        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        try:
            set_key(env_path, "RAWG_API_KEY", entered_key)
            os.environ["RAWG_API_KEY"] = entered_key
            ui.print_success("Saved RAWG API Key to .env file! (won't ask again)")
        except Exception:
            os.environ["RAWG_API_KEY"] = entered_key

        api_key = entered_key

    try:
        client = RAWGClient(api_key=api_key)
        return client
    except Exception as e:
        ui.print_error(f"Failed to initialize RAWG Client: {e}")
        sys.exit(1)


def handle_image_actions(games: list):
    """Allow user to open HD picture in Windows Photos or view in terminal."""
    if not games:
        return
    
    action = Prompt.ask(
        "\n[bold green]Type a game number (1-" + str(len(games)) + ") to open its full HD wallpaper in Windows Photos, or press Enter to continue[/bold green]",
        default="",
    ).strip()

    if action.isdigit():
        idx = int(action) - 1
        if 0 <= idx < len(games):
            selected_game = games[idx]
            img_url = selected_game.get("background_image")
            if img_url:
                ui.print_info(f"Opening full HD image for '{selected_game.get('name')}' in Windows Photos...")
                art_renderer.open_hd_image_viewer(img_url)
            else:
                ui.print_info("No HD image available for this title.")


def mode_ai_advisor(agent: GameRecommendationAgent):
    """Natural language recommendation mode."""
    console.print("\n[bold cyan][1] Ask AI Game Advisor[/bold cyan]")
    console.print("[dim]Describe what you like, e.g.:[/dim]")
    console.print("[dim][italic]  - 'I loved Elden Ring and Hollow Knight, give me challenging indie games'[/italic][/dim]")
    console.print("[dim][italic]  - 'Cozy relaxing farming or puzzle game on PC'[/italic][/dim]")
    console.print("[dim][italic]  - 'Fast-paced cyberpunk FPS with great story'[/italic][/dim]\n")

    query = Prompt.ask("[bold green]What kind of game are you looking for?[/bold green]").strip()
    if not query:
        return

    with Status("[bold cyan]Analyzing taste, querying RAWG & scanning live store deals...[/bold cyan]", spinner="dots"):
        result = agent.recommend_by_query(query)

    if not result.get("success", False):
        ui.print_error(result.get("error_note", "Failed to retrieve recommendations."))
        return

    if result.get("ai_text"):
        ui.render_ai_response(result["ai_text"])

    if result.get("summary"):
        ui.print_info(result["summary"])

    games = result.get("games", [])
    if games:
        console.print("\n[bold bright_white]Top Game Matches & Live Prices:[/bold bright_white]\n")
        for idx, game in enumerate(games[:5], 1):
            ui.render_game_card(
                game,
                index=idx,
                deal=game.get("best_deal"),
            )
        handle_image_actions(games[:5])


def mode_similar_games(agent: GameRecommendationAgent):
    """Find games similar to a target title."""
    console.print("\n[bold cyan][2] Find Games Similar to a Title[/bold cyan]")
    title = Prompt.ask("[bold green]Enter a game title (e.g. 'The Witcher 3', 'Hades', 'Cyberpunk 2077')[/bold green]").strip()
    if not title:
        return

    with Status(f"[bold cyan]Finding games similar to '{title}' and checking deals...[/bold cyan]", spinner="dots"):
        res = agent.get_similar(title)

    if not res.get("success", False):
        ui.print_error(res.get("error", "Game not found."))
        return

    target = res["target_game"]
    similar = res.get("similar_games", [])

    console.print(f"\n[bold bright_white]=== Searched Game Details ===[/bold bright_white]\n")
    ui.render_game_card(target, rationale=f"Base game searched: '{title}'", deal=target.get("best_deal"))

    if not similar:
        ui.print_info("No direct similar games found.")
        handle_image_actions([target])
        return

    console.print(f"\n[bold bright_white]=== Recommended Similar Games ===[/bold bright_white]\n")
    ui.render_game_list(similar, title=f"Games Similar to {target.get('name')}")
    
    show_details = Prompt.ask("\n[bold cyan]Show detailed cards & store deals for these similar games?[/bold cyan]", choices=["y", "n"], default="y")
    if show_details.lower() == "y":
        for idx, g in enumerate(similar[:4], 1):
            ui.render_game_card(
                g,
                index=idx,
                deal=g.get("best_deal"),
            )
        handle_image_actions([target] + similar[:4])
    else:
        handle_image_actions([target])


def mode_squad_coop(agent: GameRecommendationAgent):
    """Multi-player taste matcher for co-op games."""
    console.print("\n[bold cyan][3] Squad & Co-op Vibe Matcher[/bold cyan]")
    console.print("[dim]Find games that satisfy two players with completely different tastes![/dim]\n")

    p1 = Prompt.ask("[bold cyan]Player 1 preference (e.g., 'fast shooters with combat' or 'Elden Ring')[/bold cyan]").strip()
    p2 = Prompt.ask("[bold magenta]Player 2 preference (e.g., 'chill crafting, puzzles' or 'Stardew Valley')[/bold magenta]").strip()

    if not p1 or not p2:
        ui.print_error("Both player preferences are required.")
        return

    ui.render_squad_header(p1, p2)

    with Status("[bold cyan]Matching co-op & multiplayer games across tastes...[/bold cyan]", spinner="dots"):
        res = agent.recommend_squad_coop(p1, p2)

    if res.get("ai_text"):
        ui.render_ai_response(res["ai_text"])
    elif res.get("summary"):
        ui.print_info(res["summary"])

    games = res.get("games", [])
    if games:
        console.print("\n[bold bright_white]Squad Matches with Live Deals:[/bold bright_white]\n")
        for idx, g in enumerate(games[:4], 1):
            ui.render_game_card(g, index=idx, deal=g.get("best_deal"))
        handle_image_actions(games[:4])


def mode_live_deals(deals_client: DealsClient):
    """Dedicated live deals search across PC digital stores."""
    console.print("\n[bold cyan][5] Live Deals & Price Radar (CheapShark)[/bold cyan]")
    title = Prompt.ask("[bold green]Enter game name to check deals (e.g. 'Cyberpunk 2077', 'God of War', 'Hollow Knight')[/bold green]").strip()
    if not title:
        return

    with Status(f"[bold cyan]Scanning Steam, Epic, GOG, Humble & Fanatical for '{title}'...[/bold cyan]", spinner="dots"):
        deals = deals_client.search_deals(title, limit=8)

    ui.render_deals_table(deals, title)


def mode_guided_wizard(agent: GameRecommendationAgent):
    """Interactive step-by-step quiz."""
    console.print("\n[bold cyan][4] Guided Game Discovery Wizard[/bold cyan]")
    console.print("[dim]Answer a few quick questions to find your match:[/dim]\n")

    # 1. Genre
    genres = {
        "1": ("Action / Adventure", "action,adventure"),
        "2": ("RPG (Role-Playing)", "role-playing-games-rpg"),
        "3": ("Shooter / FPS", "shooter"),
        "4": ("Strategy / Tactical", "strategy"),
        "5": ("Indie / Cozy / Puzzle", "indie,puzzle"),
        "6": ("Horror / Survival", "action,adventure"),
        "7": ("Racing / Sports", "racing,sports"),
        "8": ("Any Genre", None),
    }
    console.print("[bold yellow]Step 1: Choose Genre[/bold yellow]")
    for k, v in genres.items():
        console.print(f"  [cyan]{k}[/cyan]. {v[0]}")
    genre_choice = Prompt.ask("Select genre", choices=list(genres.keys()), default="8")
    selected_genre = genres[genre_choice][1]

    # 2. Platform
    platforms = {
        "1": ("PC", "4"),
        "2": ("PlayStation (PS5 / PS4)", "187,18"),
        "3": ("Xbox (Series X / One)", "186,1"),
        "4": ("Nintendo Switch", "7"),
        "5": ("Any Platform", None),
    }
    console.print("\n[bold yellow]Step 2: Choose Platform[/bold yellow]")
    for k, v in platforms.items():
        console.print(f"  [cyan]{k}[/cyan]. {v[0]}")
    platform_choice = Prompt.ask("Select platform", choices=list(platforms.keys()), default="5")
    selected_platform = platforms[platform_choice][1]

    # 3. Era
    eras = {
        "1": ("Modern (2020 - Present)", "modern"),
        "2": ("Golden Era (2010 - 2019)", "golden"),
        "3": ("Classic / Retro (1990 - 2009)", "classic"),
        "4": ("Any Time", None),
    }
    console.print("\n[bold yellow]Step 3: Choose Era[/bold yellow]")
    for k, v in eras.items():
        console.print(f"  [cyan]{k}[/cyan]. {v[0]}")
    era_choice = Prompt.ask("Select era", choices=list(eras.keys()), default="1")
    selected_era = eras[era_choice][1]

    # 4. Minimum Metacritic
    min_score = IntPrompt.ask("\n[bold yellow]Step 4: Minimum Metacritic Score (0-90)[/bold yellow]", default=75)

    with Status("[bold cyan]Searching matching masterworks & active deals...[/bold cyan]", spinner="dots"):
        games = agent.wizard_recommend(
            genre=selected_genre,
            platform_id=selected_platform,
            min_metacritic=min_score,
            era=selected_era,
        )

    if not games:
        ui.print_info("No games found matching exact criteria. Try lowering the Metacritic score.")
        return

    ui.render_game_list(games, title="Wizard Recommendations")
    
    show_details = Prompt.ask("\n[bold cyan]View detailed cards & store discounts?[/bold cyan]", choices=["y", "n"], default="y")
    if show_details.lower() == "y":
        for idx, g in enumerate(games[:5], 1):
            ui.render_game_card(
                g,
                index=idx,
                deal=g.get("best_deal"),
            )
        handle_image_actions(games[:5])


def mode_top_rated(agent: GameRecommendationAgent):
    """Browse top rated games."""
    console.print("\n[bold cyan][6] Top Rated Masterpieces (Metacritic 85+)[/bold cyan]")
    with Status("[bold cyan]Fetching top rated games and store deals...[/bold cyan]", spinner="dots"):
        games = agent.rawg.get_top_rated_games(page_size=8)
        games = agent.attach_deals_to_games(games)
    
    ui.render_game_list(games, title="Top Rated Games")
    
    show_details = Prompt.ask("\n[bold cyan]View detailed cards & store discounts?[/bold cyan]", choices=["y", "n"], default="y")
    if show_details.lower() == "y":
        for idx, g in enumerate(games[:5], 1):
            ui.render_game_card(
                g,
                index=idx,
                deal=g.get("best_deal"),
            )
        handle_image_actions(games[:5])


def main():
    """Main application loop."""
    ui.render_banner()
    rawg_client = ensure_api_keys()
    agent = GameRecommendationAgent(rawg_client=rawg_client)
    deals_client = DealsClient()

    while True:
        console.print("\n[bold bright_white]=== Nexus Game Discovery Menu ===[/bold bright_white]")
        console.print("  [bold cyan]1[/bold cyan]. Ask AI Advisor (Freeform prompt / Taste description)")
        console.print("  [bold cyan]2[/bold cyan]. Find Games Similar to a Specific Title")
        console.print("  [bold cyan]3[/bold cyan]. Squad & Co-op Matcher (Multi-taste match for 2 players)")
        console.print("  [bold cyan]4[/bold cyan]. Guided Discovery Wizard (Step-by-step quiz)")
        console.print("  [bold cyan]5[/bold cyan]. Live Game Deals & Price Radar (CheapShark)")
        console.print("  [bold cyan]6[/bold cyan]. Browse Top Rated Masterpieces")
        console.print("  [bold cyan]7[/bold cyan]. Exit\n")

        choice = Prompt.ask("[bold green]Choose an option[/bold green]", choices=["1", "2", "3", "4", "5", "6", "7"], default="1")

        if choice == "1":
            mode_ai_advisor(agent)
        elif choice == "2":
            mode_similar_games(agent)
        elif choice == "3":
            mode_squad_coop(agent)
        elif choice == "4":
            mode_guided_wizard(agent)
        elif choice == "5":
            mode_live_deals(deals_client)
        elif choice == "6":
            mode_top_rated(agent)
        elif choice == "7":
            console.print("\n[bold magenta]Happy gaming! See you next time![/bold magenta]\n")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Session closed.[/dim]")
