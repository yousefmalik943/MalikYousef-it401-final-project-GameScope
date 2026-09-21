"""Refresh the local Steam 250 resilience snapshot from official HTML sources."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from services.steam250_scraper import Steam250Scraper


def main():
    scraper = Steam250Scraper(
        source_url=Config.STEAM250_URL,
        alternate_urls=[Config.STEAM250_MIRROR_URL],
        timeout=Config.SCRAPER_REQUEST_TIMEOUT,
        cache_seconds=0,
    )
    games = scraper.get_hidden_gems(limit=250)
    snapshot_path = Path(Config.STEAM250_FALLBACK_PATH)
    snapshot_path.write_text(
        json.dumps(games, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    source = "official GitHub mirror" if scraper.used_mirror else "Steam 250"
    print(f"Saved {len(games)} records from {source} to {snapshot_path.name}")


if __name__ == "__main__":
    main()
