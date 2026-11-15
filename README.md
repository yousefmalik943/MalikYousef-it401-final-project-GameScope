# GameScope

**Student:** Yousef Malik  
**Course:** IT401<br>
**Assignment:** A5 - Expanding the Web Intelligence Application with Intelligence Generation
**Application name:** GameScope

## A5 Intelligence Generation Update

GameScope now includes a retrieval-augmented recommendation feature that works on the same search results already stored in the database. Instead of returning raw records alone, the application builds a short context from the retrieved rows, asks an AI component to decide which option is strongest, validates the response, and stores the result with metadata.

### Selected intelligent capability

- Capability: Recommendation generation
- Purpose: Identify the best-fit match from the current search results.
- Why chosen: It adds decision support beyond raw retrieval while staying grounded in the application's own records.

### Retrieval-Augmented Workflow

```text
User Request
    ↓
Retrieve Relevant Records
    ↓
Build Context from Retrieved Game Records
    ↓
Generate Structured Recommendation
    ↓
Validate Response and Persist Metadata
    ↓
Display Recommendation in the Search Page
```

The AI component never invents new facts. It only works from the data already retrieved from the database.

### Prompt design

The application constructs a prompt in three parts:

1. System instructions
   - Tell the model to use only the supplied records.
   - Require valid JSON output.
   - Emphasize that the output must include `summary`, `recommendation`, `confidence`, and `supporting_items`.

2. User prompt
   - Includes the user's request such as "Recommend the best match for: tactical".
   - Explains the expected decision-making task.

3. Retrieved context
   - The app sends only the selected matching records: title, source, tag, approval, review count, and description.
   - Unnecessary information is excluded to reduce prompt noise and improve reliability.

This improves output quality because the model reasons over a tight, relevant evidence set instead of unrelated records.

### Structured output strategy

The AI response is expected to be JSON like:

```json
{
  "summary": "Across the retrieved matches, Tactical Echo stands out as the strongest fit.",
  "recommendation": "Focus on Tactical Echo first because it best matches the query and has high approval.",
  "confidence": "High",
  "supporting_items": ["Tactical Echo", "Echoes of Aether"]
}
```

### Validation and fallback behavior

Before showing or saving a generated result, the application verifies:

- required keys are present
- summary values are not empty
- recommendation values are not empty
- confidence is one of `High`, `Medium`, or `Low`
- supporting items is a non-empty list
- invalid or missing JSON is rejected

If the model is unavailable, the API key is missing, the response is malformed, or the request times out, the app falls back to a deterministic recommendation based on the retrieved result order and approval scores.

### Stored generated intelligence

The application stores:

- user request
- prompt version
- model used
- generation timestamp
- source record IDs
- output JSON
- summary
- recommendation
- confidence
- supporting item list

This metadata is useful because it documents what the model saw, what it recommended, and whether the recommendation should be trusted or reviewed later.

### AI component and environment variables

The implementation uses an OpenAI-compatible chat endpoint when `OPENAI_API_KEY` is configured.

Required or optional environment variables:

| Variable | Required | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | Optional for fallback mode | Enables live AI generation |
| `OPENAI_MODEL` | Optional | Model name such as `gpt-4o-mini` |
| `AI_REQUEST_TIMEOUT` | Optional | Timeout for AI calls in seconds |
| `DATABASE_URL` | Optional | MySQL or SQLite connection string |
| `RAWG_API_KEY` | Optional for A2/A4 data enrichment | Required for RAWG lookups |

When no API key is present, GameScope still works and generates a safe local recommendation without crashing.

### Database updates

A new `GeneratedIntelligence` model was added to persist the recommendation metadata. This table tracks each generated result and makes the intelligence part of the application's evidence trail.

### Search page and A5 experience

The main search page now shows:

- search results
- generated recommendation panel
- confidence level
- supporting items
- link to AI history

The `AI history` page stores earlier generated recommendations so the application demonstrates both generation and auditability.

### Reliability handling

The A5 workflow includes graceful handling for:

- missing API key
- rate limiting or request timeout
- empty retrieval context
- invalid model output
- generation failure
- database errors

This keeps the app usable even when the AI service is unavailable or returns bad data.

## Project Overview

GameScope is a Flask web-intelligence application for discovering PC games on
Steam. It preserves the searchable 24-game local collection created for A1 and
adds a live Hidden Gems experience. A3 adds a persistent SQLAlchemy-backed
library for information acquired from Steam 250, with web-based create, read,
update, and delete operations. The interface also combines authenticated RAWG
metadata, structured information scraped from Steam 250, and current player
reviews from Steam.

GameScope focuses on games that players rate highly but that have not yet
reached the review volume of major releases. Users can search by game title or
filter the scraped ranking by genre without changing the source code. Selecting
a result displays current metadata and representative player-review excerpts.

### What "hidden gem" means in this project

GameScope does not invent a hidden-gem label or score. It uses the ordering and
score published by Steam 250's Hidden Gems chart. That chart emphasizes games
with strong player approval and comparatively limited review exposure. The
ranking is a discovery signal rather than a guarantee that every user will like
every result.

### Application pages

| Route | Purpose | Data used |
|---|---|---|
| `/` | Introduces GameScope and links to both discovery tools | Static application content |
| `/explore` | Searches and filters the original A1 collection | `data/games.json` |
| `/hidden-gems` | Displays up to 250 Steam 250 records and enriches a search or selected game | Steam 250, RAWG, and Steam Reviews |
| `/library` | Searches and manages permanently stored records | MySQL, or local SQLite when MySQL settings are not configured |

## External Information Sources

### RAWG Video Games Database API

- Service: [RAWG API](https://rawg.io/apidocs)
- Endpoint: `GET https://api.rawg.io/api/games`
- Authentication: `RAWG_API_KEY` query parameter, loaded from the environment
- User parameter: the title entered in the Hidden Gems search form
- Fields used: title, release date, rating, rating count, Metacritic score,
  average playtime, genres, platforms, image, and source URL
- Purpose: enrich a Steam hidden-gem candidate with normalized PC game metadata

RAWG requires attribution and a link on pages where its information appears.
GameScope displays this attribution beside every API result.

### Steam 250 webpage

- Source: [Steam 250 Hidden Gems](https://steam250.com/hidden_gems)
- Official mirror: [Steam 250 generated HTML on GitHub](https://github.com/250/Steam-250/blob/gh-pages/hidden_gems.html)
- Acquisition method: `requests` and `BeautifulSoup`
- Fields extracted for each record: rank, title, Steam App ID, primary tag,
  release year, Steam 250 score, review count, approval percentage, price,
  image URL, and Steam Store URL
- Purpose: supply a current ranking of well-reviewed games with relatively low
  visibility

The scraper requests one public ranking page, identifies itself with a custom
user-agent, caches successful results for 15 minutes, and does not crawl linked
pages.

### Steam User Reviews endpoint

- Documentation: [Steam User Reviews](https://partner.steamgames.com/doc/store/getreviews)
- Endpoint: `GET https://store.steampowered.com/appreviews/<appid>?json=1`
- Fields used: review description, positive/negative totals, written review,
  recommendation, playtime, helpful votes, comment count, and developer response
- Purpose: add current, detailed player experiences to the selected result

Steam's documented endpoint returns JSON and is treated as a supporting API,
not as the assignment's HTML scraper.

## API and Web Scraping Differences

An API provides a documented machine-readable interface. GameScope sends
parameters to RAWG and Steam and processes their JSON responses using known
field names. Authentication, response codes, and rate limits are part of the
API contract.

Web scraping retrieves a webpage intended primarily for people and extracts
selected values from its HTML. GameScope uses BeautifulSoup to locate Steam
250 game cards and clean their visible text into dictionaries. Scraping is more
fragile because CSS classes and page structure can change without notice, so
the scraper checks for missing elements and reports a safe error instead of
crashing.

## Application Workflow

```text
User enters a title and/or selects a genre
                    |
                    v
Steam 250 page -> scrape and normalize ranked candidates
                    |
                    +-> validate and upsert records in SQLAlchemy database
                    +-> filter visible candidates
                    |
Selected title -> RAWG API -> normalize PC metadata
                    |
Selected App ID -> Steam Reviews -> normalize review text and summary
                    |
                    v
        Combined Hidden Gems interface and Saved Games library
```

The local `/explore` route remains separate and continues to read
`data/games.json`.

### Detailed request lifecycle

1. A request to `/hidden-gems` asks the scraper for as many as 250 ranked
  records.
2. The scraper tries the Steam 250 website first, then Steam 250's official
   generated HTML on GitHub, and finally the saved local snapshot. The interface
   shows a notice whenever the primary source was not used.
3. BeautifulSoup converts every usable HTML card into a consistently shaped
   dictionary. Incomplete cards are skipped and optional values receive safe
   defaults.
4. A selected genre filters the records by their primary Steam 250 tag. A title
   or keyword search filters the visible records by title or tag.
5. When a title is submitted, the same text is sent to RAWG as the `search`
   parameter. RAWG is limited to PC results and the first close match is
   normalized for display.
6. Choosing **View Intelligence** submits the game's numeric Steam App ID. The
   Steam Reviews endpoint returns the current review summary and representative
   English-language review excerpts.
7. Valid Steam 250 records are inserted or refreshed in the `game_records`
  table. Stable source URLs and Steam App IDs prevent repeated requests from
  producing duplicate entries.
8. Flask renders the scraped ranking, API metadata, review information,
  attribution links, and any source-specific warning on one page. `/library`
  reads saved records back from the database for search and CRUD operations.

### Source priority, caching, and data freshness

```text
Steam250.com
     | unavailable or invalid HTML
     v
Official Steam 250 GitHub mirror
     | unavailable or invalid HTML
     v
data/steam250_fallback.json (saved 250-record snapshot)
```

A successful scrape is cached in process memory for 900 seconds (15 minutes) to
reduce repeated traffic. This cache is not shared between server processes and
is cleared on restart. Separately, normalized Steam 250 records are stored
permanently in `game_records`. RAWG searches, Steam review responses, and the
24-game A1 JSON collection remain request-time or file-backed information and
are not copied into the database.

## Information Model

### Local game

- `id`, `title`, `genre`, `mode`, `price`, `rating`
- `estimated_playtime`, `release_year`, `description`, `tags`

### Scraped hidden-gem candidate

- `rank`, `title`, `steam_app_id`, `tag`, `year`
- `score`, `review_count`, `approval`, `price`
- `image`, `steam_url`

### RAWG API game

- `id`, `title`, `released`, `rating`, `ratings_count`, `metacritic`
- `playtime`, `genres`, `platforms`, `image`, `source_url`

### Steam review summary and review

- Summary: `score_description`, `total_positive`, `total_negative`,
  `total_reviews`
- Review: `text`, `recommended`, `helpful_votes`, `comment_count`,
  `playtime_hours`, `developer_response`

### Persistent database record

The `game_records` table stores each managed or acquired record with `id`,
`title`, `description`, `source`, `source_url`, `retrieved_date`, and
`created_date`. Optional Steam 250 attributes are `steam_app_id`, `rank`,
`tag`, `release_year`, `steam250_score`, `review_count`, `approval`, `price`,
and `image_url`.

Local records are fictional demonstration data stored in the repository.
Steam 250 ranking data is acquired at request time and refreshed in the
database; the ranking snapshot remains a resilience source. RAWG and Steam
reviews are displayed for the request and are not persisted.

## Application Architecture

GameScope uses a small Flask service structure so routing, external data access,
and presentation remain separate:

```text
app.py                         Flask application factory, database setup, and CLI command
config.py                      Environment variables, URLs, timeouts, and cache settings
routes/main.py                 Discovery routes, filtering, and service coordination
routes/library.py              Database-backed library CRUD routes and form validation
models/__init__.py              Flask-SQLAlchemy extension and GameRecord schema
services/persistence_service.py Maps/upserts acquired Steam 250 records
services/rawg_service.py       Authenticated RAWG request and JSON normalization
services/steam250_scraper.py   HTML fetching, parsing, retry, cache, and fallback logic
services/steam_review_service.py Steam review request and JSON normalization
services/external_errors.py    Safe application-facing external service errors
templates/                     Jinja page templates
static/                        Shared CSS, logo, and report screenshots
data/games.json                Original 24-game A1 collection
data/steam250_fallback.json    Saved 250-record resilience snapshot
scripts/refresh_steam250_snapshot.py Snapshot maintenance command
tests/test_app.py              Automated route, parser, API, and failure tests
```

`app.py` selects a configuration, initializes Flask-SQLAlchemy, registers
routes, and exposes `flask --app app init-db` for initial table creation.
`routes/main.py` coordinates discovery and acquired-record persistence;
`routes/library.py` validates CRUD form input. External services normalize
their responses, and expected source failures are presented as readable
notices without preventing unaffected data from being displayed.

## Environment Variables

| Variable | Required | Description |
|---|---:|---|
| `RAWG_API_KEY` | Yes for RAWG search | Private key issued by RAWG |
| `SECRET_KEY` | Recommended | Flask session/security secret |
| `DATABASE_URL` | Optional | SQLAlchemy connection URL; use the CI-Keys MySQL URL when supplied |
| `MYSQL_HOST` | Optional | MySQL server hostname, when not using `DATABASE_URL` |
| `MYSQL_PORT` | Optional | MySQL port; defaults to `3306` |
| `MYSQL_USER` | Optional | MySQL username |
| `MYSQL_PASSWORD` | Optional | MySQL password |
| `MYSQL_DATABASE` | Optional | Existing MySQL schema/database name |
| `FLASK_ENV` | No | `development` or `production` |
| `OPENAI_API_KEY` | Optional for fallback mode | Enables live AI generation |
| `OPENAI_MODEL` | Optional | Model name such as `gpt-4o-mini` |
| `AI_REQUEST_TIMEOUT` | Optional | Timeout for AI calls in seconds |

Set either `DATABASE_URL` or the `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`,
and `MYSQL_DATABASE` values to use MySQL. The application selects the
`mysql+pymysql` driver for MySQL. If no database settings are present, it uses
a persistent SQLite file in Flask's instance directory for local development
and automated tests. The real `.env` file is excluded through `.gitignore`;
`.env.example` contains variable names only.

## Installation Instructions

1. Clone the repository and enter its directory.

   ```bash
   git clone <repository-url>
   cd MalikYousef-it401-final-project-GameScope-main
   ```

2. Create and activate a virtual environment.

   ```bash
   python -m venv .venv
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies.

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Register for a free key at [RAWG](https://rawg.io/apidocs).

5. Copy `.env.example` to `.env` and add the private key.

   ```dotenv
   RAWG_API_KEY=your_private_key_here
   SECRET_KEY=your_random_secret_here
  DATABASE_URL=mysql+pymysql://username:password@host:3306/database?charset=utf8mb4
   ```

  Use the MySQL connection values provided through CI-Keys. URL-encode special
  characters in a `DATABASE_URL`, or provide the `MYSQL_*` settings separately.
  The database/schema must already exist and the account must be allowed to
  create tables. Leave `DATABASE_URL` empty to use local SQLite instead.

6. Initialize the tables.

  ```bash
  flask --app app init-db
  ```

7. Start the application.

   ```bash
   python app.py
   ```

8. Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

If PowerShell prevents activation of the virtual environment, the application
can still be run by addressing its Python executable directly:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Do not place a key directly in `rawg_service.py`, `api_service.py`, or another
Python file. Restart the Flask server after changing `.env`, because environment
values are read during application startup.

## Using the Application

### Browse the local collection

1. Open **Local Collection**, or visit `/explore`.
2. Enter a keyword or choose a genre, play mode, and minimum rating.
3. Submit the form. Matching local games are sorted from highest to lowest
   rating.
4. Clear the form to restore all 24 demonstration records.

### Discover and investigate hidden gems

1. Open **Hidden Gems**, or visit `/hidden-gems`. An unfiltered load displays
   up to all 250 ranked records from the active Steam 250 source.
2. Select a genre to filter by the primary tag supplied by Steam 250.
3. Enter a title or keyword to filter the cards and request matching RAWG
   metadata. The RAWG information panel appears when a match is returned.
4. Select **View Intelligence** on a card to request its Steam review summary
   and detailed review excerpts. The selected App ID is validated before any
   Steam request is made.
5. Follow the displayed source links to inspect the original information.

Genre filtering is based on the one primary tag available in each Steam 250
record. A game may have additional Steam genres that are not represented by
that tag. A search can also return fewer than 250 cards because the filtering
is intentionally applied to the complete ranking.

### Intelligent recommendations

1. Enter a title or keywords on the **Hidden Gems** page and submit the form.
2. After the normal search results appear, review the new **AI Recommendation**
   panel.
3. The panel shows the AI's top choice, confidence level, and supporting games.
4. Follow the links to view the detailed game information or inspect another
   source.
5. The recommendation is based on the same data you can see; it is not a
   hidden or secret result.

The AI component enhances the discovery experience by highlighting the most
promising match from the current results. It does not replace the normal
search and exploration features.

## Dependencies

| Package | Role |
|---|---|
| Flask | Routing, configuration, and Jinja template rendering |
| Flask-SQLAlchemy | ORM models, database sessions, and SQLAlchemy integration |
| PyMySQL | MySQL DBAPI driver |
| Requests | HTTP calls to RAWG, Steam 250, its mirror, and Steam Reviews |
| Beautiful Soup | Parsing and cleaning the Steam 250 HTML |
| python-dotenv | Loading private configuration from `.env` |
| pytest | Automated application and service tests |

Exact minimum versions are listed in `requirements.txt`.

## Maintaining the Steam 250 Snapshot

The checked-in snapshot keeps the assignment demonstrable during a Steam 250
DNS or network outage. Refresh it only when one of the official HTML sources is
available:

```bash
python scripts/refresh_steam250_snapshot.py
```

The command uses the same parser as the web application, requests up to 250
records, writes formatted JSON to `data/steam250_fallback.json`, and reports the
source and number of saved records. Review the resulting Git diff before
committing it. The snapshot is public ranking data; it must never contain an API
key or other secret.

## Current Features

- Responsive Flask homepage and shared navigation
- Searchable and filterable 24-game local collection from A1
- Live Steam 250 Hidden Gems HTML scraper
- Structured extraction and cleaning of multiple game records
- Title search sent as a parameter to the authenticated RAWG API
- PC metadata normalization from RAWG JSON
- Current Steam review summaries and detailed review excerpts
- Genre filtering and title/keyword searching
- Source links and attribution in the interface
- Fifteen-minute scraper cache to limit repeated requests
- A dedicated 30-second scraper timeout for slower Steam 250 responses
- Automatic retries for temporary DNS, connection, and server failures
- Steam 250's official GitHub `gh-pages` mirror as a secondary live HTML source
- A 250-game attributed Steam 250 snapshot used only when the live source is down
- Graceful handling of invalid input and external-source failures
- MySQL persistence for acquired Steam 250 information
- Searchable saved-record library with create, read, update, and delete actions
- Required-field, URL, length, and duplicate validation
- Automated tests that do not require live external services
- AI-generated recommendations based on search results
- AI recommendation history and auditability

## Error Handling

- **Missing API key:** the page explains that `RAWG_API_KEY` must be added to
  `.env`; scraped results remain usable.
- **Invalid input:** title length is limited, unknown genre values are ignored,
  and Steam App IDs must contain digits only.
- **API authentication failure:** a safe message asks the user to check the key.
- **Rate limits:** HTTP 429 responses produce a wait-and-retry message.
- **Network failure or timeout:** each source has a timeout and its own readable
  notice rather than a Flask error page. Steam 250 falls back to a saved,
  clearly labeled snapshot so the page remains demonstrable.
- **Empty API results:** the user is told no matching PC game was found.
- **Missing HTML fields:** incomplete Steam 250 records are skipped and optional
  fields receive safe defaults.
- **Changed webpage structure:** if no records can be extracted, the page reports
  that the format may have changed.
- **Empty reviews:** the page retains the review summary and explains that no
  written English reviews were returned.
- **AI component unavailable:** the recommendation panel shows a fallback message
  and the last known good recommendation, if available.

## Ethical Considerations

- GameScope identifies its scraper and makes only one cached request to the
  Steam 250 ranking instead of crawling the site.
- Steam 250, RAWG, and Steam are visibly attributed and linked.
- RAWG's free-plan attribution and request limits must be followed.
- Only public player reviews are requested through Steam's documented endpoint.
- GameScope does not collect Steam IDs or attempt to identify reviewers.
- Review excerpts remain the opinions of their authors and should not be treated
  as objective facts.
- Site policies and `robots.txt` should be checked again before deploying the
  application or increasing request volume.

## Security and Privacy

- Secrets are loaded from the ignored `.env` file and are never rendered in a
  template or placed in a source URL shown to users.
- `.env.example` contains names and placeholders only, so it is safe to commit.
- Search input is trimmed and length-limited; App IDs must be numeric and genre
  values must come from the application's allowlist.
- Jinja auto-escaping remains enabled for values rendered into HTML.
- The application does not use user accounts, persist searches, or collect
  reviewer identities.
- The default `SECRET_KEY=dev` fallback is suitable only for local development.
  A random value should be supplied through `.env` for deployment.

## Known Limitations

- External information requires an internet connection.
- RAWG title matching may choose a similarly named game.
- Steam 250 exposes one primary tag per ranking record, so genre filtering does
  not represent every tag a game has on Steam.
- The Steam endpoint provides review text and comment counts but not the full
  discussion beneath a review.
- Ranking and price data may change between visits.
- A redesign of Steam 250's HTML may require selector updates.
- The in-memory scraper cache resets when the Flask process restarts.
- The saved 250-record Steam 250 fallback may be older than the live ranking.
- A high approval percentage with few reviews is a discovery signal, not proof
  that every player will enjoy the game.

## Testing

Run the automated suite with:

```bash
python -m pytest -q
```

Tests cover the homepage, local filters, HTML extraction, missing credentials,
combined API/scraper rendering, and graceful external failure handling. Network
responses are mocked so the tests are repeatable and do not consume API limits.

At the time of this update, the suite contains 10 passing tests. Run it again
after any route, parser, template, or service change rather than relying on that
recorded count.

## Troubleshooting

### The browser says the page is unreachable

- Confirm that the terminal running `python app.py` is still open and shows a
  local address such as `http://127.0.0.1:5000`.
- Use that local address directly; do not substitute a Bing search redirect or
  another website URL.
- If port 5000 is already occupied, stop the older Flask process before starting
  another instance.
- After editing `.env`, stop the server with `Ctrl+C` and start it again.

## Quick database reset

If the local SQLite database accumulates stale data during development or testing, reset it before rerunning the app or tests:

```bash
rm -f gamescope.db
flask --app app reset-db
```

This recreates the schema without leaving old records behind and avoids false search-result counts from previous debug runs.

### A5 screenshots

The application now includes a search page with ranked results and a recommendation panel, plus a saved generation history view for auditing prior AI outputs.

![A5 Search Page](static/images/a5-search-page.png)

![Generated Intelligence](static/images/a5-generated-intelligence.png)

![Validation and Fallback Handling](static/images/a5-error-handling.png)

![AI History](static/images/a5-history.png)

These screenshots show the requested A5 user flow: query-driven search, best-match recommendation generation, structured output, validation, and stored historical records.