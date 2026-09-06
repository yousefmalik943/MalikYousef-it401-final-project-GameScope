# GameScope

**Student:** Yousef Malik  
**Course:** IT401  
**Assignment:** A1 - Customize and Extend the IT401 Project Template

## Project Overview

GameScope is a Web Intelligence application designed to help PC gamers
discover video games that better match their interests. The application
organizes game information and allows users to search and filter games by
genre, game mode, rating, and keywords.

Many game-discovery platforms emphasize popularity, sales, or overall
ratings. These measurements do not always explain why players enjoy a game
or whether its specific strengths and weaknesses match an individual
player's preferences. GameScope addresses this problem by providing a more
focused and explainable discovery experience.

The application's intended users include PC gamers, Steam users, players
looking for niche or independent games, and anyone having difficulty
deciding what game to play or purchase next.

## Preliminary Semester Project Concept

The planned direction for GameScope is to develop it from a local
JSON-powered Flask application into a Web Intelligence system for intelligent
video game discovery. Future versions will acquire publicly accessible game
metadata and review information from Steam or another appropriate source,
store relevant information in a database, and allow users to retrieve and
compare games.

The intelligent component will analyze review text and game characteristics
to identify commonly praised features, recurring player concerns, and
similarities between games. These insights can support explainable
recommendations and help users understand why a particular game may or may
not match their interests.

Major features planned for the semester include:

- Acquiring game metadata and public review information from external sources
- Persisting game, review, preference, and generated-insight data
- Searching and filtering a larger game collection
- Comparing games using genres, tags, ratings, and engagement information
- Analyzing review sentiment and recurring review topics
- Generating explainable game recommendations
- Identifying niche, older, or under-recognized "hidden gem" games
- Using private library or playtime information only when a user explicitly
  authorizes access

This is a preliminary concept. The project scope, APIs, and information model
may be refined after Module 2 as available information sources and technical
requirements are evaluated.

## Current Features

The A1 version of GameScope currently includes:

- A customized responsive homepage
- An original GameScope logo
- Shared navigation and footer elements through `base.html`
- A separate `/explore` Flask route
- Eight sample games loaded from a local JSON file
- Keyword searching across titles, descriptions, genres, modes, and tags
- Genre filtering
- Game-mode filtering
- Minimum-rating filtering
- Combined filtering using multiple criteria
- Game-result cards displaying important game information
- A clear message when no games match the selected filters
- Automated tests for the homepage, Explore page, and filtering behavior

## Information Model (Conceptual)

GameScope currently manages a collection of sample video games stored in
`data/games.json`. Each game contains the following attributes:

- `id`: Unique identifier for the game
- `title`: Name of the game
- `genre`: Primary game genre
- `mode`: Single-player, multiplayer, or cooperative play
- `price`: Example purchase price
- `rating`: Example positive rating percentage
- `estimated_playtime`: Approximate number of gameplay hours
- `release_year`: Year the game was released
- `description`: Short explanation of the game
- `tags`: Searchable characteristics associated with the game

Later versions may expand the information model to include:

- Developers and publishers
- Real game identifiers from an external source
- Player-review text
- Positive and negative review themes
- User preferences
- Authorized user playtime
- Game-similarity scores
- Recommendation explanations
- Hidden-gem or discovery scores

A formal database schema is not required for A1. The current JSON structure
provides a simple conceptual model that can later be transferred into a
persistent database.

## Project Structure

```
project/
├── app.py                 # App factory, entry point
├── config.py               # Environment-based configuration
├── routes/                  # View functions
├── requirements.txt
├── services/                # Business logic and external integrations
│   ├── api_service.py       # Generic outbound HTTP client
│   ├── search_service.py    # Search logic
│   └── ai_service.py        # AI/LLM integration
├── models/                  # Data models
├── templates/                # Jinja2 HTML templates
├── static/                   # CSS, JS, images
├── data/                      # Local data files
└── tests/                      # Test suite
```

## Prerequisites

- Python 3.10+
- Git

## Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd project
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv

   # macOS / Linux
   source .venv/bin/activate

   # Windows (Command Prompt / PowerShell)
   .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Running the App

With the virtual environment activated:

```bash
python app.py
```

The app will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000).

By default it runs in development mode. Set `FLASK_ENV=production` to use the production config.

## Configuration

Configuration lives in `config.py` and reads from environment variables:

| Variable            | Description                          |
|---------------------|---------------------------------------|
| `SECRET_KEY`         | Flask secret key                      |
| `API_KEY`             | Key for external API service          |
| `AI_SERVICE_API_KEY`   | Key for AI service integration        |
| `FLASK_ENV`             | `development` or `production`         |

## Testing

With the virtual environment activated:

```bash
python -m pytest tests/
```
