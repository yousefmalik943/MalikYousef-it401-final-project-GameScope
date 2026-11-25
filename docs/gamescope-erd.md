# GameScope ERD

The original library and A4/A5 history remain independent. A6 adds profiles,
immutable decision runs, display impressions, and one editable feedback row per
run. `catalog_snapshots` stores the latest validated chart without claiming an
unknown-date bundled snapshot is live. No existing table columns were changed.

```mermaid
erDiagram
  STEAM_CATALOG_INDEXES {
    int id PK
    longtext apps_json
    datetime fetched_at
    bool complete
  }
  STEAM_DISCOVERY_GAMES {
    string app_id PK
    datetime checked_at
    bool eligible
    text data_json
  }
  PLAYER_PROFILES ||--o{ DECISION_RUNS : requests
  DECISION_RUNS ||--o{ DECISION_IMPRESSIONS : displays
  DECISION_RUNS ||--o| DECISION_FEEDBACK : receives
  PLAYER_PROFILES {
    string id PK
    string steam_id UK
    longtext games_json
    datetime synced_at
    text sync_note
  }
  DECISION_RUNS {
    string id PK
    string profile_id FK
    datetime created_at
    string strategy_version
    text context_json
    text options_json
  }
  DECISION_IMPRESSIONS {
    int id PK
    string run_id FK
    datetime shown_at
    text displayed_json
  }
  DECISION_FEEDBACK {
    int id PK
    string run_id FK,UK
    string action
    string selected_app_id
    int usefulness
    text comment
    datetime created_at
  }
  CATALOG_SNAPSHOTS {
    int id PK
    string source_mode
    datetime fetched_at
    datetime saved_at
    longtext games_json
  }
  STEAM_LOGIN_ATTEMPTS {
    string token PK
    datetime created_at
    bool consumed
  }
  SEARCH_EVENTS {
    int id PK
    string query
    datetime created_at
    int result_count
  }
  GENERATED_INTELLIGENCES {
    int id PK
    text source_record_ids
    text output_data
    datetime generated_at
  }
  GAME_RECORDS {
    int id PK
    string title
    text description
    string source
    string source_url UK
    datetime retrieved_date
    datetime created_date
    string steam_app_id UK
    int rank
    string tag
    string release_year
    string steam250_score
    int review_count
    int approval
    string price
    string image_url
  }
```
