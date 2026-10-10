from __future__ import annotations

from dataclasses import asdict, dataclass
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from urllib import error, parse, request

import chess

from chess_memoriser.cache import ResponseCache
from chess_memoriser.position import position_key
from chess_memoriser.result import count_wdl, distribution


OFFICIAL_ENDPOINT = "https://explorer.lichess.org/lichess"
ALL_RATINGS = (0, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500)
ALL_SPEEDS = ("ultraBullet", "bullet", "blitz", "rapid", "classical", "correspondence")
_LIVE_REQUEST_LOCK = threading.Lock()
_LAST_LIVE_REQUEST = 0.0


@dataclass(frozen=True)
class LichessFilters:
    ratings: tuple[int, ...] = ALL_RATINGS
    speeds: tuple[str, ...] = ALL_SPEEDS
    since: str = "1952-01"
    until: str = "3000-12"

    def validate(self) -> None:
        if not self.ratings or any(value not in ALL_RATINGS for value in self.ratings):
            raise ValueError(f"Ratings must be one or more of {ALL_RATINGS}")
        if not self.speeds or any(value not in ALL_SPEEDS for value in self.speeds):
            raise ValueError(f"Speeds must be one or more of {ALL_SPEEDS}")

    @property
    def key(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def params(self, board: chess.Board) -> dict[str, str | int]:
        return {
            "variant": "standard",
            "fen": f"{position_key(board)} 0 1",
            "speeds": ",".join(self.speeds),
            "ratings": ",".join(map(str, self.ratings)),
            "since": self.since,
            "until": self.until,
            # 256 exceeds the maximum legal-move count, avoiding display truncation.
            "moves": 256,
            "topGames": 0,
            "recentGames": 0,
            "history": "false",
        }


class LichessExplorerError(RuntimeError):
    pass


class LichessAdapter:
    def __init__(
        self,
        cache: ResponseCache,
        *,
        filters: LichessFilters | None = None,
        legacy_cache: Path | None = None,
        token: str | None = None,
        endpoint: str = OFFICIAL_ENDPOINT,
        delay: float = 3.0,
    ):
        self.cache = cache
        self.filters = filters or LichessFilters()
        self.filters.validate()
        self.legacy_cache = Path(legacy_cache).resolve() if legacy_cache else None
        self.token = token if token is not None else os.environ.get("LICHESS_TOKEN", "").strip()
        self.endpoint = endpoint
        self.delay = max(0.0, delay)

    def _legacy_get(self, key: str) -> dict | None:
        if self.filters != LichessFilters() or not self.legacy_cache or not self.legacy_cache.is_file():
            return None
        try:
            db = sqlite3.connect(f"file:{self.legacy_cache}?mode=ro", uri=True, timeout=10)
            row = db.execute(
                "SELECT fetched,raw FROM snapshots WHERE position=? AND source='lichess'",
                (key,),
            ).fetchone()
            db.close()
        except sqlite3.Error:
            return None
        if not row:
            return None
        return {"fetched_at": row[0], "endpoint": "legacy-cache", "payload": json.loads(row[1])}

    @staticmethod
    def _validate(board: chess.Board, payload: dict) -> None:
        for field in ("white", "draws", "black"):
            if type(payload.get(field)) is not int or payload[field] < 0:
                raise LichessExplorerError(f"Invalid Explorer position count: {field}")
        if not isinstance(payload.get("moves"), list):
            raise LichessExplorerError("Explorer response has no moves array")
        seen: set[str] = set()
        for item in payload["moves"]:
            for field in ("white", "draws", "black"):
                if type(item.get(field)) is not int or item[field] < 0:
                    raise LichessExplorerError("Invalid Explorer move count")
            try:
                # Explorer uses UCI_Chess960 castling notation (king-to-rook,
                # e.g. e1h1) even for standard chess. parse_uci normalises it
                # to the standard board move (e1g1), matching local adapters.
                move = board.parse_uci(item["uci"])
            except (KeyError, ValueError):
                raise LichessExplorerError("Invalid Explorer UCI move") from None
            normalized = move.uci()
            if move not in board.legal_moves or normalized in seen:
                raise LichessExplorerError(f"Illegal or duplicate Explorer move: {item['uci']}")
            seen.add(normalized)
        if sum(count_wdl(move) for move in payload["moves"]) > count_wdl(payload):
            raise LichessExplorerError("Explorer continuation counts exceed the position total")

    def _live_get(self, board: chess.Board) -> dict:
        global _LAST_LIVE_REQUEST
        query = parse.urlencode(self.filters.params(board))
        headers = {"Accept": "application/json", "User-Agent": "chess-memoriser/0.1"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(f"{self.endpoint}?{query}", headers=headers)
        with _LIVE_REQUEST_LOCK:
            for attempt in range(3):
                time.sleep(max(0.0, self.delay - (time.monotonic() - _LAST_LIVE_REQUEST)))
                _LAST_LIVE_REQUEST = time.monotonic()
                try:
                    with request.urlopen(req, timeout=60) as response:
                        return json.load(response)
                except error.HTTPError as exc:
                    if exc.code == 401 and not self.token:
                        raise LichessExplorerError(
                            "Explorer authentication is required. Set LICHESS_TOKEN or pass --token-file. "
                            "A token with no OAuth scopes is sufficient."
                        ) from None
                    if exc.code in (401, 403):
                        raise LichessExplorerError("Explorer authentication failed; check the supplied token") from None
                    if exc.code not in (429, 500, 502, 503, 504):
                        raise LichessExplorerError(f"Explorer HTTP {exc.code}") from None
                    if attempt == 2:
                        raise LichessExplorerError(f"Explorer unavailable after retries (HTTP {exc.code})") from None
                    wait = 60.0 if exc.code == 429 else 5.0 * (2**attempt)
                    retry_after = exc.headers.get("Retry-After", "")
                    try:
                        wait = max(wait, float(retry_after))
                    except ValueError:
                        try:
                            wait = max(wait, parsedate_to_datetime(retry_after).timestamp() - time.time())
                        except (TypeError, ValueError):
                            pass
                    time.sleep(wait)
                except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                    if attempt == 2:
                        raise LichessExplorerError(f"Explorer network/response failure: {exc}") from None
                    time.sleep(5.0 * (2**attempt))
        raise AssertionError("unreachable")

    def query(self, board: chess.Board, *, refresh: bool = False, offline: bool = False) -> dict:
        key = position_key(board)
        cached = None if refresh else self.cache.get("lichess", key, self.filters.key)
        origin = "local_cache"
        if cached is None and not refresh:
            cached = self._legacy_get(key)
            origin = "reused_legacy_cache"
        if cached is None:
            if offline:
                raise LichessExplorerError("No matching cached Lichess response and --offline was requested")
            payload = self._live_get(board)
            self._validate(board, payload)
            fetched = self.cache.put("lichess", key, self.filters.key, self.endpoint, payload)
            cached = {"fetched_at": fetched, "endpoint": self.endpoint, "payload": payload}
            origin = "live_api"
        else:
            self._validate(board, cached["payload"])

        payload = cached["payload"]
        return distribution(
            board,
            source="lichess_player_games",
            metadata={
                "adapter": "lichess_opening_explorer",
                "endpoint": self.endpoint,
                "authentication": "OAuth2 bearer credential available for live calls" if self.token else "no live credential available",
                "cache_origin": origin,
                "fetched_at": cached["fetched_at"],
                "population": "Aggregated rated games from Lichess players",
                "filters": asdict(self.filters),
                "complete_move_list_requested": True,
            },
            position_wdl={name: payload[name] for name in ("white", "draws", "black")},
            move_rows=[{
                "uci": board.parse_uci(item["uci"]).uci(),
                **{name: item[name] for name in ("white", "draws", "black")},
            } for item in payload["moves"]],
            limitations=[
                "The Explorer is an aggregate service; underlying games and any upstream deduplication are not exposed here.",
                "The selected rating buckets describe Lichess's indexed rating groups, not the installed master population.",
                "A 256-move request is used so percentages cover all returned legal continuations, not a display-limited subset.",
            ],
        )
