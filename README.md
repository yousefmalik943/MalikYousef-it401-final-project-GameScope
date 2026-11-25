# GameScope

**Student:** Yousef Malik  
**Course:** IT401<br>
**Assignment:** A6 - Explainable Decision Support and Steam Personalization
**Application name:** GameScope

## Community-inspired interface

GameScope's A6 interface presents game discovery as a welcoming place to explore.
Soft greens, cream backgrounds, rounded white panels, colorful game artwork, and
friendly illustrations give the application a playful identity while keeping
recommendation evidence, confidence, and decision controls easy to find.

### Inspiration and visual direction

The primary visual inspiration is **Nintendo's Miiverse**, specifically the
reference screenshot supplied by the project owner. Its green surroundings,
white community panels, game-image tiles, and handwritten drawing accents shaped
the direction. Nintendo's [official Miiverse overview](https://www.nintendo.co.jp/hardware/wiiu/miiverse/index.html)
describes its game communities and handwritten posts, which provide context for
the welcoming, expressive reference design.

GameScope adapts those visual cues with its own branding, controller illustration,
navigation icons, and doodles. Steam supplies game information and artwork. The
interface's community-inspired appearance supports personal game discovery;
features shown in the screenshots are GameScope's actual discovery and decision
tools.

| Reference cue | GameScope adaptation | Purpose |
|---|---|---|
| Green surroundings and white community panels | A soft green dotted background with cream and white cards | Separates sections while keeping the page welcoming |
| Game-image community tiles | A two-column home-page collection board and illustrated recommendation cards | Makes games easier to recognize and explore |
| Handwritten drawings and expressive faces | Original controller doodles, speech bubbles, stars, hearts, and a friendly note card | Adds personality around the functional content |
| Simple, approachable navigation | Icon-based discovery sidebar, active-page indicators, and a Your plans shortcut | Keeps the main tools and saved decisions accessible |
| Rounded, compact panels | Rounded forms, category chips, confidence badges, and comparison sections | Organizes inputs and evidence into readable groups |

### What changed on each screen

- **Home:** a welcome panel, original controller artwork, collection tiles, and a
  short guide to linking Steam, choosing a path, and comparing recommendations.
  The artwork board is labeled as a preview from the saved Steam 250 collection.
- **Shared navigation:** desktop pages use a discovery sidebar. Smaller screens
  use a compact navigation grid. The current section stays highlighted, including
  history and record-editing views.
- **Play Next:** a three-step navigation strip connects play history, path
  preferences, and the comparison. Connected-account information and style signals
  sit in separate panels; optional explanatory material uses expandable sections.
- **Recommendation details:** game artwork introduces each card, followed by its
  role, confidence, sourced genres/tags, reasoning, suggested trial, and evidence.
- **Comparison and feedback:** options remain comparable in a table, with the
  accept/reject/alternative decision form and optional usefulness rating below it.
- **History:** saved primary and alternative titles appear in individual cards,
  with links back to their original comparisons and feedback.
- **Phone layouts:** panels and cards stack vertically, form controls remain
  usable, and wide comparison tables can scroll inside their own container.

### A6 UI screenshots

These screenshots were captured from the running Flask application at **1440px
desktop** and **390px phone** widths. Long pages use selected regions so the
relevant controls and evidence stay readable. The linked Steam account identifier
is hidden in the presentation captures. The game titles, recommendation evidence,
and saved history remain application output.

**Home page — desktop**

![GameScope desktop home page showing the discovery sidebar, welcome panel, game-art collection board, and illustrated note cards](static/images/a6-ui/a6-home-desktop.png)

| Screenshot | View | What it demonstrates |
|---|---|---|
| [Home — desktop](static/images/a6-ui/a6-home-desktop.png) | 1440px | Overall visual direction, original artwork, sidebar, and collection board |
| [Home — phone](static/images/a6-ui/a6-home-mobile.png) | 390px | Compact navigation and vertically arranged welcome and discovery panels |
| [Play Next — desktop](static/images/a6-ui/a6-planner-desktop.png) | 1440px | Connected-account panel, style signals, and the start of the plan builder |
| [Play Next — phone](static/images/a6-ui/a6-planner-mobile.png) | 390px | Stacked account and style panels on a narrow screen |
| [Plan controls — phone](static/images/a6-ui/a6-planner-mobile-controls.png) | 390px | Category, discovery path, avoidance chips, and generation controls |
| [Recommendation detail — desktop](static/images/a6-ui/a6-planner-desktop-cards.png) | 1440px | Game artwork, confidence, source labels, explanation, and Steam actions |
| [Recommendation detail — phone](static/images/a6-ui/a6-planner-mobile-cards.png) | 390px | Recommendation content and evidence in a single-column layout |
| [Comparison and feedback](static/images/a6-ui/a6-comparison-feedback.png) | 1440px | Option comparison, decision choices, usefulness rating, and comments |
| [Comparison — remaining columns](static/images/a6-ui/a6-comparison-details.png) | 1440px | The same table scrolled horizontally to show reviews, price, ownership, and confidence |
| [Recommendation history](static/images/a6-ui/a6-history-desktop.png) | 1440px | Saved game titles, alternatives, strategy versions, and plan links |

<details>
<summary>View Play Next and decision-support screenshots</summary>

**Play Next overview**

![Play Next desktop overview with separate account and style panels above the plan builder](static/images/a6-ui/a6-planner-desktop.png)

**Recommendation detail**

![Recommendation card with game artwork, confidence, sourced category labels, reasoning, and actions](static/images/a6-ui/a6-planner-desktop-cards.png)

**Comparison and feedback**

![Game comparison table and decision feedback form in the community-inspired theme](static/images/a6-ui/a6-comparison-feedback.png)

The comparison can scroll horizontally when long game titles make the table
wider than its panel. This second view shows the remaining columns:

![Horizontally scrolled comparison showing review counts, quoted prices, ownership, and confidence](static/images/a6-ui/a6-comparison-details.png)

**Saved recommendation history**

![Recommendation history with saved game titles and links to earlier plans](static/images/a6-ui/a6-history-desktop.png)

</details>

<details>
<summary>View phone screenshots</summary>

**Home**

<img src="static/images/a6-ui/a6-home-mobile.png" alt="Phone home page with compact navigation and stacked discovery panels" width="300">

**Plan controls**

<img src="static/images/a6-ui/a6-planner-mobile-controls.png" alt="Phone plan builder showing category and avoidance controls" width="300">

**Recommendation detail**

<img src="static/images/a6-ui/a6-planner-mobile-cards.png" alt="Phone recommendation detail with game artwork and evidence" width="300">

</details>

### Implementation and usability checks

The shared theme lives in `static/community.css`, layered over
`static/style.css`. `templates/base.html` supplies the shared navigation and
footer. Original SVG assets are `gamescope-community.svg`, `community-icons.svg`,
and `community-doodles.svg` in `static/images/`. GameScope's recommendation rules
and historical plans are preserved by the visual update.

The read-only `/game-artwork/<appid>` helper resolves Steam's current artwork URL,
including newer hashed asset paths. It permits HTTPS Steam CDN images and uses
the original illustrated fallback when artwork is unavailable. Successful lookups
cache for one day; failed lookups cache for five minutes in a bounded in-process
cache.

Browser checks cover Home and Play Next at desktop and phone widths, including
horizontal overflow and artwork loading. The UI also includes a skip link,
visible keyboard-focus states, reduced-motion support, and distinct confidence
labels. The latest automated application check passed **71 tests**, including
artwork URL validation, caching, and service-failure handling.

## A6 Decision Support

### Steer away from familiar styles (A6-v4)

Choose **Step outside my usual styles** to use play history as a reference for
distance rather than similarity. The existing strict exclusion of usual categories
still applies. The new **Categories to steer away from** checkboxes let the user
explicitly exclude Action, Adventure, RPG, or any supported category, even if it
falls below the automatically inferred usual-style threshold. Every primary and
alternative must avoid those categories, including mixed-genre games and category
knowledge combined across Steam and chart rows. Required categories remain strict;
an explicit required/avoided conflict produces a readable notice.

For broad exploration, leave Required category unset. Explicit avoidance can also
supply the reference without a Steam import. With neither history nor explicit
avoidance, the app explains that it cannot determine what to steer away from.

Eligible discovery candidates are ranked by a documented category-distance
heuristic with three broad design families:

- Action, Adventure, RPG, Horror, Platformer, Roguelike
- Puzzle, Strategy, Simulation, Casual
- Racing, Sports

Same-category similarity is 1, different categories in the same family have
similarity .5, and categories in different families have similarity 0. Distance
is `1 - max(similarity(candidate_category, reference) × reference_weight)` across
all resolved candidate categories and reference styles. Reference weights use the
normalized play-history affinities, with explicit exclusions and usual categories
assigned weight 1. Ranking awards 65 points for distance, 25 for approval and 10
for review support. Thus an Action/Adventure/RPG profile tends to surface more
distant categories such as Puzzle, Strategy, or Simulation rather than another
nearby action-oriented category. These families and weights are design choices,
not learned evidence of literal opposites, pace, mood, difficulty, or enjoyment.

Random selection remains weighted and runs only after strict filters. Discovery
alternatives prefer different displayed categories when available. Games already
shown anywhere in the profile's history remain excluded by default; the history
opt-in resets to unchecked on each new form. No small-pool fallback reintroduces
a blocked or previously recommended game. Individual distance scores, explanations,
explicit exclusions and evidence are saved with strategy version **A6-v4**. Earlier
plans remain immutable historical snapshots.

### Strict categories and non-repeating discovery (A6-v3)

Selected categories are now eligibility requirements for the primary and every
alternative. Choosing Roguelike requires a sourced Roguelike, Roguelite, Action
Roguelike, Traditional Roguelike, Rogue-like/lite, or Roguelike Deckbuilder tag
(or an equivalent exact genre label). Adventure, Action, or RPG alone never
establish a roguelike. Original labels remain visible in each card's **Sourced
genres and tags** with a category-evidence link; the app does not relabel games
to make them pass a filter. Explicit compound tags can support both families,
such as Puzzle Platformer → Puzzle and Platformer.

Steam's app-details genres are broad. The exact App ID's public store page now
supplies popular user-defined tags via a narrowly scoped HTML parser. Up to thirty
tags are retained. Missing, age-gated, unavailable, or mismatched pages do not
justify guessing a missing category. Each newly qualified Steam game can require
a third request for its tags. Each generation can also upgrade up to eight existing
positive cache entries missing tags, with at most four workers and a one-day retry
interval for unsuccessful tag lookups. Review acquisition timestamps remain
unchanged by tag enrichment. Steam 250's sourced primary tags remain valid backup
category evidence; App ID deduplication prevents duplicate cards across sources.

**Explore a different style** is also strict. A usual style is a resolved gameplay
category with at least half the relative weight of the strongest style in the
sampled played games. Candidates with **any** recognized genre/tag overlapping
those usual categories are rejected, even if another displayed category is new.
The plan lists excluded usual styles. With no resolved Steam styles, the app
explains that it cannot verify novelty. Selecting a usual category together with
the different-style path produces a clear conflict notice; it does not override
either requirement. Syncing Steam also reads tags for the five played-game samples,
so a new sync improves the precision of the inferred style profile.

Before ranking, A6-v3 excludes every game App ID shown as primary or alternative
in **any saved plan for the current profile**, including plans older than ten runs.
Empty plans do not consume games. Random selection only uses the remaining eligible
candidates. It never fills an incomplete comparison with a prior recommendation
or a game outside the selected category. One or two matches remain one or two;
an exhausted pool shows an explanatory empty state. The optional **Include games
from my recommendation history** checkbox explicitly allows repeats while keeping
ownership and category/path requirements. Refreshing a saved page preserves its
contents; the generate button requests a new set.
Repeated submission of the same rendered form uses an idempotent generation ID,
so a double click does not create a duplicate saved plan.

Steam-wide retrieval prioritizes matching chart seeds even after the initial pool
has grown and can supplement the cache when it has fewer than three *unseen,
filter-matching* direct candidates. Final filtering always runs after retrieval.
Both modes use 65 points for verified category fit/novelty, 25 for approval, and
10 for review support; novelty is a strict gate rather than a small score bonus.
Saved plans identify the **A6-v3** strategy. Earlier plans remain unchanged and show
a notice that their original rules differ. The v1/v2 sections below document those
historical strategies where they differ from v3.

### Steam-wide discovery, varied plans, and named history (A6-v2)

Play Next now defaults to **Steam-wide discovery**. This uses
[Steam's GetAppList](https://partner.steamgames.com/doc/webapi/IStoreService#GetAppList)
to index the broader game catalog rather than limiting discovery to Steam 250.
It does not import Steam's personalized recommendation feed or access Steam's
internal database. GameScope generates its own recommendations from public evidence.

The catalog is paginated in batches of 50,000 with a bounded fetch budget (at most
ten requests, stopping between requests after 25 seconds). A partial index is
explicitly identified. The index is cached for 24 hours. Each new Steam-wide plan
checks at most 16 randomly sampled, unowned games not successfully checked within
seven days, using four workers. Each inspection has at most one store-data request
and one review-summary request, with a six-second per-request timeout. The initial
catalog load and scans may take longer than chart-only plans.

While the directly verified pool has fewer than twelve entries, up to four of
those sixteen checks can be seeded from an already-acquired chart. The remaining
checks explore Steam's wider index. Seeds still undergo the same direct Steam
metadata/review checks; explanations identify chart-seeded versus wider-catalog
discoveries. This supplies initial options while the broader verified pool grows.

GameScope's **own hidden-gem criteria** are released Windows games with **20–5,000
reviews** and **at least 85% positive** reviews. These are discovery heuristics,
not a Steam-certified hidden-gem label or proof of low sales/player counts. Review
summaries request all languages, both recommendation types, all purchase sources,
and Steam's off-topic filtering. The unrounded positive/total ratio determines
eligibility; the display rounds approval to a whole percentage.

Steam's public `store.steampowered.com/api/appdetails` endpoint supplies exact-App-ID
titles, genres, release/platform flags, and US-region price quotes. This endpoint
is **undocumented**, may change, and is isolated in
`services/steam_discovery_service.py`. The documented
[GetAppReviews endpoint](https://partner.steamgames.com/doc/webapi/IUserReviewsService#GetAppReviews)
supplies approval/count evidence. Qualifying candidates and successful negative
checks are cached for seven days. Transport failures are not cached as negative
results. Candidates from expired checks are excluded until rechecked. Any eligible
indexed game can enter the random scan, but this is not exhaustive evaluation of
every game and not every click will find new qualifying games.

The growing pool lives in additive `steam_catalog_indexes` and
`steam_discovery_games` tables, separately from chart snapshots and manual records.
They store public game data, not account identifiers. When fewer than three direct
Steam candidates are available, the Steam 250 pool supplements them. The interface
discloses this and each card preserves its own source, acquisition date and evidence
link. Direct candidates are not described as Steam 250 ranked games. Multi-genre
Steam candidates use the category best matching the selected style or play history.
Select **Steam 250 hidden-gem chart** to use the previous source alone.

New plans retain category/quality scoring, then vary selection among up to 30
candidates within 20 points of the highest score. Draw weight is
`max(1, score)^2 / (1 + 3 × appearances_in_last_ten_plans)`. If at least three of
these candidates were absent from the last plan, that unseen subset is used.
If fewer than three candidates are within that score range, the next-best options
expand the pool to three (or all eligible options if fewer). Such options may have
weaker personal fit; their scores/confidence are not inflated. The primary avoids
the last primary when another eligible choice exists. Alternatives prefer the same
pool and otherwise fill from the remaining ranking. Alternatives can repeat when
the pool is small, and a single eligible candidate must repeat as primary;
randomization never fabricates new evidence. Confidence still reflects evidence
strength, not randomness. The strategy version is saved as **A6-v2**.

**Recommendation history** (`/play-next/history`) lists primary and alternative
game titles with dates, confidence, and strategy versions, twenty plans per page.
The dashboard lists the latest ten. Opening a historical plan preserves the exact
options originally shown; only generating a new plan reruns discovery/selection.
History remains scoped to the current browser or verified Steam profile.

The older `/appreviews/<appid>?json=1` endpoint is deprecated and now redirects
to the store homepage in live checks. Both discovery and the Hidden Gems review
panel now use `IUserReviewsService/GetAppReviews/v1/`, JSON service parameters,
numeric filter enums, and the `response` envelope. This public review API does
not need a publisher key. See Steam's
[migration guide](https://partner.steamgames.com/doc/webapi/IUserReviewsService#migrating).

**Decision problem:** Which lesser-known Steam game should I try next, and why?
**Target user:** PC players looking beyond familiar popular games, including players
who want recommendations connected to their Steam activity.

Open **Play Next** (`/play-next`) from the navigation. The dedicated interface
shows a primary recommendation, up to two alternatives, a comparison table,
evidence, confidence explanations, an exploratory time plan, and a decision form.
It uses public Steam evidence and/or acquired Steam 250 candidates; the fictional
A1 collection is excluded.

### Running and demonstrating A6

```bash
python -m pip install -r requirements.txt
flask --app app init-db
python app.py
```

`init-db` is additive: it creates missing A6 tables without resetting existing
records. Do not run `reset-db` to upgrade. No existing table columns were added,
so this update needs no column migration. Supported databases remain SQLite and MySQL.

1. Open `http://127.0.0.1:5000/play-next`.
2. Choose a candidate source, **Strategy**, **Stay close to my style**, and a
   30-minute exploratory trial. Generate a plan. Steam-wide mode scans beyond
   the chart; chart mode can use a bundled snapshot when both chart hosts fail.
3. Inspect the primary choice and alternatives. Each identifies its selection
   factors, chart evidence, known limitations, and confidence rules.
4. Compare category, style fit, total ranking score, approval, review count,
   source-quoted price, visible ownership, and confidence in the table.
5. Accept, reject, select an alternative, or rate usefulness. Rating and comments
   are optional for accept/reject/alternative decisions. Save and revisit the plan
   to demonstrate persistence. Updating feedback replaces the current decision
   for that plan rather than counting duplicate submissions as separate decisions.
6. Inspect your plan-view count, decision count, rating count, and average
   usefulness in **Your recent plans**. An unrated plan has no invented rating.

### Link Steam and personalize from actual play

Configure these server environment values in your uncommitted `.env`:

```dotenv
SECRET_KEY=<a-private-random-value-of-at-least-32-characters>
STEAM_WEB_API_KEY=<your-server-side-Steam-Web-API-key>
RAWG_API_KEY=<your-RAWG-key>
PUBLIC_BASE_URL=http://127.0.0.1:5000
```

Generate a secret with `python -c 'import secrets; print(secrets.token_hex(32))'`.
Obtain a server key through [Steam Web API registration](https://steamcommunity.com/dev/apikey).
Restart Flask after editing `.env`. The browser origin must exactly match
`PUBLIC_BASE_URL`: `localhost` and `127.0.0.1` are different origins. On a deployed
site use its HTTPS origin, `FLASK_ENV=production`, and a private random secret.
Steam linking is disabled until a sufficiently long non-placeholder secret is set.

Choose **Sign in through Steam**. Steam authenticates the account on its own
domain using [OpenID](https://steamcommunity.com/dev); GameScope verifies the
assertion with Steam rather than trusting a submitted profile ID. Callback checks
include fixed provider, claimed identity, signed fields, exact return URL, nonce
age, browser state, and a database-backed one-time login attempt. No password is
collected. A returning verified Steam account restores its GameScope profile.

After linking, choose **Sync Steam history**. The consent text explains that this
imports visible owned games and recent/lifetime playtime, and sends at most five
played titles to RAWG for genre enrichment. `GetOwnedGames` and
`GetRecentlyPlayedGames` use the server key and the verified Steam ID through
[IPlayerService](https://partner.steamgames.com/doc/webapi/IPlayerService).
The user does not provide a personal API key. OpenID verifies identity; it does
not grant access to private game details. Users must expose Game details and
playtime for this import to work.

The five highest-weight played games supply style signals. A game's weight is:

```text
0.70 × ln(1 + recent minutes) + 0.30 × ln(1 + lifetime minutes)
```

Recent minutes represent Steam's last-two-weeks activity, not a daily schedule.
Weights are divided among each seed game's RAWG genres, summed by broad category,
and normalized against the strongest category. The explicit category mapping is
in `services/decision_support.py` (for example JRPG → RPG and RTS → Strategy).
This mapping is a design heuristic, not verified equivalence of game mechanics.
RAWG enrichment requires a normalized exact title match. This reduces unrelated
matches but does not resolve same-name games or edition ambiguity by Steam ID.
Unresolved genres are omitted and reported. No game styles are guessed from titles.

Played games and their recent/lifetime hours appear as evidence alongside genre
source links. The imported visible library excludes owned candidates from the
plan. Without an import, ownership is explicitly unknown. Sync is user initiated;
there is no background Steam polling. A failed/private-library sync clears the
active import so new plans cannot silently use stale history. Previously saved
plans remain historical snapshots until the user deletes them.

**Disconnect and delete** removes the profile, imported history, saved plans,
display telemetry, and decision feedback. Anonymous profiles are browser-session
scoped; clearing browser cookies loses access to anonymous history. Linked profiles
can be restored by verifying the same Steam account. POST actions use CSRF tokens,
and saved plans/feedback are scoped to the current profile.

### Decision Workflow Diagram

```mermaid
flowchart TD
    A[Choose preferences or verify Steam account] --> B[Import visible play history]
    A --> C[Retrieve acquired Steam 250 chart]
    B --> D[Resolve up to five played-game genres with RAWG]
    C --> E[Exclude visible owned games and rank candidates]
    D --> E
    E --> F[Generate evidence-based explanations and confidence]
    F --> G[Save primary recommendation and up to two alternatives]
    G --> H[Display comparison and record rendered options]
    H --> I[Accept / Reject / Select alternative / Rate usefulness]
    I --> J[Persist feedback and show evaluation counts]
```

### Explainability and alternatives

Decision logic lives in `services/decision_support.py`, separately from acquisition
in `services/decision_retrieval.py`, the existing A5 intelligence service, and Flask
routes in `routes/decisions.py`. Explanations are deterministic statements assembled
from retrieved fields and computed factors. A6 does not require or call an LLM.
Consequently, AI downtime does not prevent generating, comparing, or selecting a plan.

Style fit combines 60% stated-category match and 40% behavioral-category affinity
when both are available; either supplies the entire fit when the other is absent.
With neither, fit is zero and confidence is Low.

| Path | Fit | Category novelty | Approval | Review support |
|---|---:|---:|---:|---:|
| Stay close to my style | 65 | 0 | 25 | 10 |
| Explore a different style | 45 | 20 | 25 | 10 |

Scores are weighted points out of 100. Approval uses the chart's percentage.
Review support is `min(1, ln(1 + review_count) / ln(1001))`. Category novelty is
`1 - behavioral affinity` and only contributes when Steam styles and a candidate
category exist. The discovery path changes scoring emphasis; it does not claim
to be a difficulty progression or an in-game walkthrough. Trial minutes do not
alter rankings because session suitability is not supported by current evidence.

A6-v1 saved plans used the highest-ranked candidate and the next two distinct
candidates. New A6-v2 plans use the varied selection described above. Ranking ties
break by chart rank, then Steam App ID. Fewer eligible candidates produce fewer
alternatives with an explanation rather than fabricated options.

### Confidence and limitations

Confidence describes evidence strength, **not the probability of enjoyment**:

- **High:** fit at least 60%, two supporting played games, history synced within
  seven days, source evidence fetched within two days, valid approval, and at least 100 reviews.
- **Medium:** fit at least 60%, known category, source evidence fetched within two days,
  valid approval, and a positive review count, without all High conditions.
- **Low:** the remaining cases, including unknown-date snapshots, missing rating
  evidence, and unsupported personal fit. The suggestion remains usable with caveats.

The latest chart has separate original-fetch and local-save timestamps. Cached
acquisitions retain original fetch time; bundled snapshot acquisition time is
unknown. Both decision UI and Hidden Gems distinguish snapshot data from live data.
The decision engine only uses the latest acquired chart, so historical library
rows that dropped out of the chart do not remain eligible through database search.
Prices are historical source quotes without a guaranteed currency region or sale
freshness; users verify current prices and availability on Steam.

RAWG average playtime is not completion time or recommended session length. Steam
playtime does not establish enjoyment, free time, personality, mood, or skill.
The displayed time plan is an explicitly labeled user-chosen exploratory trial;
save systems, pause support, difficulty progression, and optimal session length
are unverified. A candidate has only one chart tag, and the five-game style sample
may miss important preferences. Genre enrichment can add up to five external
requests during sync; slow/unavailable sources produce unresolved-style notices.

### User Feedback and Decision Telemetry

Additive tables:

| Table | Stored information |
|---|---|
| `catalog_snapshots` | Latest validated chart JSON, source mode, original fetch time if known, local save time |
| `player_profiles` | Browser profile ID, optional verified Steam ID, imported visible library/history, sync time and notice |
| `steam_login_attempts` | Random one-time authentication token, creation time, consumed status |
| `decision_runs` | Profile, request preferences, strategy version, creation time, provenance, immutable options/evidence/confidence |
| `decision_impressions` | Plan ID, render timestamp, displayed App IDs and confidence labels |
| `decision_feedback` | Plan ID, accept/reject/alternative/rate action, selected App ID, optional 1–5 rating/comment, decision timestamp |

Impressions record server-rendered plans, not proof that a person read the page.
Feedback is one current decision per plan and can be updated. Missing feedback is
not interpreted as rejection; comments and ratings are nullable. Old plans keep
their original evidence and confidence after a chart refresh or history sync.
Feedback is currently used for evaluation, not automatic reranking. Future tuning
could compare acceptance, alternative selection, and usefulness across path and
confidence groups. Such comparisons need enough observations and must account for
exposure and selection bias. A chosen game does not establish that it was enjoyed.

### Reliability

- No Steam key, private details, missing playtime, missing RAWG key, or unresolved
  styles: explain the limitation and allow manual style selection.
- Recent-history API failure: explicitly fall back to lifetime-only evidence.
- Chart host failures: mirror, then labeled bundled snapshot; no source: readable
  error and retry. Refresh respects the existing 15-minute scraper cache.
- Empty/fully owned chart: save an empty plan and show a clear empty state without
  a broken comparison or feedback form.
- Low confidence or missing evidence: display the limitations and available fields.
- Database failure: rollback and return a readable 503 page; do not claim feedback
  was saved. Invalid CSRF, feedback values, or option IDs are rejected.
- A5 model failures still use local fallback; engine metadata now reflects the
  actual path, supporting titles are checked against retrieved records, and local
  fallback confidence is Low. Output shape validation does not prove factuality.

### Evaluation

Run `python -m pytest -q`. Tests use database configuration applied **before**
SQLAlchemy initialization, preventing the normal development database from being
used for test table creation/deletion. Cases cover behavioral ranking, owned-game
exclusion, confidence degradation, alternatives/comparison rendering, immutable
plans, optional feedback, validation, CSRF, profile isolation, private-history
fallback, deletion, title mismatch, OpenID response verification, and callback replay.
The tests use controlled service responses; they do not prove live account access.

Use the Play Next metrics to evaluate actual interaction. Usefulness is the mean
of submitted ratings only; report the rating count beside it. A manual evaluation
should include a public account, a private account, no recent playtime, unknown
genres, network failure, and a user selecting each decision type. Compare whether
users report that explanations and alternatives help them decide. No user study
or recommendation-quality result is claimed by this implementation. Live Steam
sign-in/import requires configured keys, a running callback origin, and an account
owner completing sign-in; these cannot be substituted by test fixtures.

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

The AI component is instructed to use only retrieved database records. Validation
checks structure and supporting titles, but cannot guarantee factual correctness.

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
- Endpoint: `GET https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/`
- Parameters: `input_json`, including App ID, language list, and numeric review/purchase/filter enums
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
