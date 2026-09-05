# 🎮 Video Game Recommendation Agent & Deal Radar (Terminal CLI)

An intelligent, terminal-based AI game recommendation agent and live price scanner that combines **RAWG Database (500k+ games)**, **CheapShark Live Digital Store Deals**, and **Google Gemini AI**.

---

## ✨ Standout Features

- 💬 **Conversational AI Advisor**: Freeform natural language query processing (*"I loved Elden Ring and Hollow Knight, give me indie dark fantasy games on PC"*).
- 🏷️ **Live Deals & Price Radar**: Automatically scans authorized digital stores (Steam, Epic Games, GOG, Humble Store, Fanatical) for active discounts, sale prices, and savings percentages.
- 🎨 **Terminal ANSI Pixel Art Covers**: Converts official box cover art into truecolor pixel art directly in your terminal!
- 👥 **Squad & Co-op Matcher**: Solves the dilemma of two friends with different tastes wanting to game together by finding the perfect middle-ground co-op games.
- 🧭 **Guided Discovery Wizard**: Step-by-step interactive questionnaire (Genre, Platform, Era, Metacritic threshold).
- 🎮 **Similar Games Matcher**: Finds titles mechanically and atmospherically similar to any game title.
- 🏆 **Top-Rated Showcase**: Browse the highest-rated games of all time or recent eras.

---

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys
Create a `.env` file in the project folder (or copy `.env.example`):
```env
RAWG_API_KEY=your_rawg_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here  # Optional: For AI reasoning
```
> **Get Free Keys:**
> - RAWG API Key: [rawg.io/apidocs](https://rawg.io/apidocs)
> - Gemini API Key: [aistudio.google.com](https://aistudio.google.com/)
> - *CheapShark API is 100% free and requires no key!*

### 3. Run the Agent
```powershell
.venv\Scripts\python main.py
```
*(or `python main.py`)*
