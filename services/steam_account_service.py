"""Steam authentication and public play history. No Steam passwords are collected."""
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests

from services.external_errors import ExternalServiceError

OPENID_ENDPOINT = "https://steamcommunity.com/openid/login"
OPENID_NS = "http://specs.openid.net/auth/2.0"
IDENTIFIER = "http://specs.openid.net/auth/2.0/identifier_select"


class SteamAccountService:
    def __init__(self, api_key=None, timeout=10, session=None):
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or requests.Session()

    @staticmethod
    def login_url(return_to, realm):
        return OPENID_ENDPOINT + "?" + urlencode({
            "openid.ns": OPENID_NS, "openid.mode": "checkid_setup",
            "openid.return_to": return_to, "openid.realm": realm,
            "openid.identity": IDENTIFIER, "openid.claimed_id": IDENTIFIER,
        })

    def verify_login(self, args, return_to):
        # Never trust an ID supplied in a query string without provider verification.
        fields = {key: value for key, value in args.items() if key.startswith("openid.")}
        required_signed = {"op_endpoint", "claimed_id", "identity", "return_to", "response_nonce", "assoc_handle"}
        claimed = fields.get("openid.claimed_id", "")
        match = re.fullmatch(r"https://steamcommunity\.com/openid/id/(7656119\d{10})", claimed)
        if (fields.get("openid.ns") != OPENID_NS
                or fields.get("openid.mode") != "id_res"
                or fields.get("openid.op_endpoint") != OPENID_ENDPOINT
                or fields.get("openid.return_to") != return_to
                or fields.get("openid.identity") != claimed or not match
                or not required_signed.issubset(set(fields.get("openid.signed", "").split(",")))):
            raise ExternalServiceError("Steam sign-in could not be verified. Please start again.")
        try:
            nonce_time = datetime.strptime(fields.get("openid.response_nonce", "")[:20], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if not -60 <= (datetime.now(timezone.utc) - nonce_time).total_seconds() <= 600:
                raise ValueError("expired")
            fields["openid.mode"] = "check_authentication"
            response = self.session.post(OPENID_ENDPOINT, data=fields, timeout=self.timeout, allow_redirects=False)
            if response.status_code != 200 or "is_valid:true" not in response.text.splitlines():
                raise ValueError("unverified")
        except (ValueError, requests.RequestException) as exc:
            raise ExternalServiceError("Steam sign-in expired or could not be verified. Please try again.") from exc
        return match.group(1)

    def _get(self, method, params):
        if not self.api_key:
            raise ExternalServiceError("Steam library sync needs STEAM_WEB_API_KEY on the server. You can still choose a style below.")
        try:
            response = self.session.get(
                f"https://api.steampowered.com/IPlayerService/{method}/v0001/",
                params={"key": self.api_key, "input_json": json.dumps(params)},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json().get("response")
            if not isinstance(payload, dict):
                raise ValueError("invalid response")
            return payload
        except (ValueError, AttributeError, requests.RequestException) as exc:
            # Do not include exception URLs: they may contain the server API key.
            raise ExternalServiceError("Steam play history is unavailable or rate limited. Try syncing again later.") from exc

    def get_play_history(self, steam_id):
        owned = self._get("GetOwnedGames", {"steamid": steam_id, "include_appinfo": True, "include_played_free_games": True})
        if not isinstance(owned.get("games"), list):
            raise ExternalServiceError("Steam returned no visible library. Set Game details to Public, including playtime, or choose a style manually.")
        note = ""
        try:
            recent = self._get("GetRecentlyPlayedGames", {"steamid": steam_id, "count": 0})
            recent_games = recent.get("games", [])
            if not isinstance(recent_games, list):
                raise ExternalServiceError("Invalid recent history")
        except ExternalServiceError:
            recent_games = []
            note = "Recent history was unavailable; this sync uses lifetime playtime."
        recent_by_id = {str(g.get("appid")): g for g in recent_games if isinstance(g, dict)}
        games = []
        for item in owned["games"]:
            if not isinstance(item, dict) or not str(item.get("appid", "")).isdigit():
                continue
            app_id = str(item["appid"])
            recent_item = recent_by_id.get(app_id, {})
            def minutes(value):
                try:
                    return max(0, int(value or 0))
                except (TypeError, ValueError):
                    return 0
            games.append({
                "app_id": app_id, "title": str(item.get("name") or f"Steam app {app_id}")[:200],
                "recent_minutes": minutes(recent_item.get("playtime_2weeks", item.get("playtime_2weeks"))),
                "lifetime_minutes": minutes(item.get("playtime_forever")),
                "genres": [],
            })
        return games, note
