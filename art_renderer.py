"""Module to fetch, render, and display game images in HD or high-density terminal format."""

import io
import os
import tempfile
import webbrowser
from typing import Optional
import requests
from PIL import Image


def image_url_to_ansi(image_url: str, target_width: int = 60) -> Optional[str]:
    """Download image and convert to high-density ANSI truecolor representation."""
    if not image_url or not image_url.startswith("http"):
        return None

    try:
        resp = requests.get(image_url, timeout=6)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        
        orig_w, orig_h = img.size
        aspect_ratio = orig_h / orig_w
        target_height = int(target_width * aspect_ratio)
        if target_height % 2 != 0:
            target_height += 1
        
        target_height = min(max(target_height, 14), 28)
        resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        pixels = resized.load()

        lines = []
        for y in range(0, target_height, 2):
            row_chars = []
            for x in range(target_width):
                r_top, g_top, b_top = pixels[x, y]
                if y + 1 < target_height:
                    r_bot, g_bot, b_bot = pixels[x, y + 1]
                else:
                    r_bot, g_bot, b_bot = (0, 0, 0)

                ansi_block = f"\033[38;2;{r_top};{g_top};{b_top}m\033[48;2;{r_bot};{g_bot};{b_bot}m▀\033[0m"
                row_chars.append(ansi_block)
            lines.append("".join(row_chars))

        return "\n".join(lines)
    except Exception:
        return None


def open_hd_image_viewer(image_url: str) -> bool:
    """Download the full HD image and open it in the default system image viewer / Windows Photos."""
    if not image_url or not image_url.startswith("http"):
        return False

    try:
        resp = requests.get(image_url, timeout=8)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        
        # Save temporary file and open with system default viewer
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "game_hd_cover.jpg")
        img.save(temp_path, "JPEG")
        
        # Open in default Windows viewer
        os.startfile(temp_path)
        return True
    except Exception:
        # Fallback to browser URL
        return webbrowser.open(image_url)
