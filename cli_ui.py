import sys
import re
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown

import art_renderer

console = Console(force_terminal=True)


def format_metacritic(score: Optional[int]) -> Text:
    """Format Metacritic score badge with color coding."""
    if score is None:
        return Text("N/A", style="dim")
    if score >= 85:
        return Text(f"[{score}]", style="bold green")
    elif score >= 70:
        return Text(f"[{score}]", style="bold yellow")
    elif score >= 50:
        return Text(f"[{score}]", style="bold orange3")
    else:
        return Text(f"[{score}]", style="bold red")


def format_rating(rating: Optional[float]) -> str:
    """Format numerical rating cleanly."""
    if not rating:
        return "N/A"
    return f"{rating:.1f} / 5.0"


def clean_html(raw_html: Optional[str]) -> str:
    """Strip HTML tags from game descriptions."""
    if not raw_html:
        return "No description available."
    clean = re.sub(r"<.*?>", "", raw_html)
    return " ".join(clean.split())


def render_banner():
    """Render the application banner."""
    banner_text = r"""[bold cyan] _  _ _____ _  _ _   _ ___  [/bold cyan]  [bold magenta]  ___   _   __  __ ___ [/bold magenta]
[bold cyan]| \| | ____\ \/ / | | / __| [/bold cyan]  [bold magenta] / __| /_\ |  \/  | __|[/bold magenta]
[bold cyan]| .` |  _|  >  <| |_| \__ \ [/bold cyan]  [bold magenta]| (_ |/ _ \| |\/| | _| [/bold magenta]
[bold cyan]|_|\_|_____/_/\_\\___/|___/ [/bold cyan]  [bold magenta] \___/_/ \_\_|  |_|___|[/bold magenta]"""
    console.print(Panel(banner_text, border_style="bright_blue", expand=False))


def render_game_card(
    game: Dict[str, Any],
    index: Optional[int] = None,
    rationale: Optional[str] = None,
    deal: Optional[Dict[str, Any]] = None,
    show_terminal_art: bool = False,
):
    """Render a single detailed game card with HD image link and deal info."""
    name = game.get("name", "Unknown Game")
    title_prefix = f"[{index}] " if index else ""

    # High-Density in-terminal art preview if requested
    if show_terminal_art and game.get("background_image"):
        art = art_renderer.image_url_to_ansi(game["background_image"], target_width=55)
        if art:
            console.print(f"\n[bold dim]--- HD Preview: {name} ---[/bold dim]")
            print(art)
            console.print()

    # Extract details
    rating = game.get("rating", 0)
    metacritic = game.get("metacritic")
    released = game.get("released", "TBA")
    
    # Platforms
    platforms_raw = game.get("platforms", []) or []
    platform_names = [p.get("platform", {}).get("name", "") for p in platforms_raw if p.get("platform")]
    platforms_str = ", ".join(platform_names[:5]) if platform_names else "Multiple Platforms"

    # Genres
    genres_raw = game.get("genres", []) or []
    genre_names = [g.get("name", "") for g in genres_raw]
    genres_str = " | ".join(genre_names[:4]) if genre_names else "General"

    # Stores / RAWG URL & HD Image
    slug = game.get("slug", "")
    rawg_url = f"https://rawg.io/games/{slug}" if slug else ""
    bg_image = game.get("background_image", "")

    # Build content
    content = Text()
    content.append("Rating: ", style="bold")
    content.append(f"{format_rating(rating)}  ", style="gold1")
    content.append("Metacritic: ", style="bold")
    content.append_text(format_metacritic(metacritic))
    content.append(f"  Released: {released}\n", style="white")

    content.append("Platforms: ", style="bold")
    content.append(f"{platforms_str}\n", style="cyan")

    content.append("Genres: ", style="bold")
    content.append(f"{genres_str}\n", style="magenta")

    # Live Deal Badge
    if deal:
        content.append("\nLive Best Deal: ", style="bold yellow")
        sale_p = deal.get("sale_price", 0.0)
        norm_p = deal.get("normal_price", 0.0)
        store = deal.get("store", "Store")
        savings = deal.get("savings_percent", 0)

        if savings > 0:
            content.append(f"${sale_p:.2f} ", style="bold green")
            content.append(f"(was ${norm_p:.2f}, -{savings:.0f}% OFF) ", style="bold bright_yellow")
            content.append(f"on {store}\n", style="bold cyan")
        else:
            content.append(f"${norm_p:.2f} on {store}\n", style="white")
        
        if deal.get("deal_url"):
            content.append("   Deal Link: ", style="dim")
            content.append(f"{deal['deal_url']}\n", style="underline blue")

    if rationale:
        content.append("\nWhy Recommended: ", style="bold bright_yellow")
        content.append(f"{rationale}\n", style="italic bright_white")

    # Short description
    description = clean_html(game.get("description_raw") or game.get("description", ""))
    if description and description != "No description available.":
        if len(description) > 260:
            description = description[:257] + "..."
        content.append(f"\n{description}\n", style="dim white")

    if bg_image:
        content.append("\nHD Cover Image: ", style="bold green")
        content.append(f"{bg_image}\n", style="underline bright_cyan")

    if rawg_url:
        content.append("RAWG Database: ", style="bold dim")
        content.append(f"{rawg_url}", style="underline blue")

    card_panel = Panel(
        content,
        title=f"[bold bright_white]{title_prefix}{name}[/bold bright_white]",
        border_style="bright_magenta",
        padding=(0, 2),
    )
    console.print(card_panel)


def render_game_list(games: List[Dict[str, Any]], title: str = "Recommended Games"):
    """Render a clean summary table of games."""
    if not games:
        console.print(Panel("[yellow]No games found matching your criteria.[/yellow]", border_style="yellow"))
        return

    table = Table(title=f"[Results] {title}", border_style="bright_blue", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Game Title", style="bold white", min_width=24)
    table.add_column("Metacritic", justify="center", width=12)
    table.add_column("User Rating", justify="center", width=14)
    table.add_column("Released", justify="center", width=10)
    table.add_column("Platforms", style="cyan", min_width=20)
    table.add_column("Genres", style="magenta", min_width=18)

    for idx, game in enumerate(games, 1):
        name = game.get("name", "Unknown")
        meta = format_metacritic(game.get("metacritic"))
        rating = f"{game.get('rating', 0):.1f}/5"
        released = str(game.get("released", "TBA"))[:4]
        
        platforms_raw = game.get("platforms", []) or []
        p_names = [p.get("platform", {}).get("name", "") for p in platforms_raw if p.get("platform")]
        platforms = ", ".join(p_names[:3]) if p_names else "Various"

        genres_raw = game.get("genres", []) or []
        genres = ", ".join([g.get("name", "") for g in genres_raw][:2]) if genres_raw else "N/A"

        table.add_row(str(idx), name, meta, rating, released, platforms, genres)

    console.print(table)


def render_deals_table(deals: List[Dict[str, Any]], game_title: str):
    """Render live price deals comparison table."""
    if not deals:
        console.print(Panel(f"[yellow]No active digital store discounts found for '{game_title}'.[/yellow]", border_style="yellow"))
        return

    table = Table(title=f"[Deals] Live Deals & Discounts for '{game_title}'", border_style="green", show_header=True, header_style="bold green")
    table.add_column("Store", style="bold cyan", width=18)
    table.add_column("Sale Price", justify="right", style="bold green", width=12)
    table.add_column("Regular Price", justify="right", style="dim strike", width=14)
    table.add_column("Discount", justify="center", style="bold yellow", width=12)
    table.add_column("Store / Deal URL", style="underline blue")

    for d in deals:
        sale = f"${d['sale_price']:.2f}"
        regular = f"${d['normal_price']:.2f}"
        savings = f"-{d['savings_percent']:.0f}%" if d['savings_percent'] > 0 else "0%"
        url = d.get("deal_url", "N/A")
        table.add_row(d["store"], sale, regular, savings, url)

    console.print(table)


def render_squad_header(p1_taste: str, p2_taste: str):
    """Render the co-op squad matchmaking header."""
    squad_text = f"""[bold cyan]Player 1 Vibe:[/bold cyan] {p1_taste}
[bold magenta]Player 2 Vibe:[/bold magenta] {p2_taste}
[bold yellow]Mission:[/bold yellow] Finding cooperative & multiplayer games that bridge both worlds!"""
    console.print(Panel(squad_text, title="[bold green][Squad Matchmaker] Co-op Matchmaker[/bold green]", border_style="bright_yellow"))


def render_ai_response(text: str):
    """Render markdown-formatted AI response."""
    console.print(Panel(Markdown(text), title="[bold green][AI Advisor] Nexus Recommendation[/bold green]", border_style="green", padding=(1, 2)))


def print_error(msg: str):
    """Print error message in red panel."""
    console.print(Panel(f"[bold red][ERROR][/bold red] {msg}", border_style="red"))


def print_info(msg: str):
    """Print informational message in cyan."""
    console.print(f"[bold cyan][INFO] {msg}[/bold cyan]")


def print_success(msg: str):
    """Print success message in green."""
    console.print(f"[bold green][OK] {msg}[/bold green]")
