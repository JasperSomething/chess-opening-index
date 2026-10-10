from __future__ import annotations

from pathlib import Path

from chess_memoriser.adapters.lichess import LichessAdapter, LichessFilters
from chess_memoriser.adapters.master import MasterDatabaseAdapter
from chess_memoriser.cache import ResponseCache
from chess_memoriser.position import ParsedPosition
from chess_memoriser.result import unavailable_distribution


def position_state(parsed: ParsedPosition) -> dict:
    """Return the board state needed by the GUI without touching either database."""
    return {
        "position": parsed.as_dict(),
        "legal_moves": [
            {"uci": move.uci(), "san": parsed.board.san(move)}
            for move in parsed.board.legal_moves
        ],
    }


def query_sources(
    parsed: ParsedPosition,
    *,
    cache_path: Path,
    master_db: Path,
    legacy_lichess_cache: Path | None,
    filters: LichessFilters,
    token: str | None = None,
    offline: bool = False,
    refresh: bool = False,
) -> dict:
    try:
        with ResponseCache(cache_path) as cache:
            lichess = LichessAdapter(
                cache,
                filters=filters,
                legacy_cache=legacy_lichess_cache,
                token=token,
            ).query(parsed.board, refresh=refresh, offline=offline)
    except (OSError, ValueError, RuntimeError) as exc:
        lichess = unavailable_distribution(
            "lichess_player_games",
            {"population": "Aggregated rated games from Lichess players", "filters": filters.__dict__},
            str(exc),
        )
    try:
        with MasterDatabaseAdapter(master_db) as masters:
            master = masters.query(parsed.board)
    except (OSError, ValueError, RuntimeError) as exc:
        master = unavailable_distribution(
            "installed_master_database",
            {"database": str(Path(master_db).resolve()), "population": "both players rated 2200+"},
            str(exc),
        )
    return {
        "schema_version": 1,
        **position_state(parsed),
        "distributions": {
            "lichess_player_games": lichess,
            "installed_master_database": master,
        },
    }
