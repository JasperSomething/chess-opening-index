from __future__ import annotations

import chess


def count_wdl(item: dict) -> int:
    return sum(item[name] for name in ("white", "draws", "black"))


def distribution(
    board: chess.Board,
    *,
    source: str,
    metadata: dict,
    position_wdl: dict[str, int] | None,
    move_rows: list[dict],
    limitations: list[str],
) -> dict:
    continuation_games = sum(count_wdl(row) for row in move_rows)
    position_games = count_wdl(position_wdl) if position_wdl is not None else None
    terminal_games = position_games - continuation_games if position_games is not None else None
    if terminal_games is not None and terminal_games < 0:
        limitations = [*limitations, "Move totals exceed the reported position total; terminal count is unavailable."]
        terminal_games = None

    moves = []
    for row in move_rows:
        move = chess.Move.from_uci(row["uci"])
        games = count_wdl(row)
        moves.append(
            {
                "uci": row["uci"],
                "san": board.san(move),
                "games": games,
                "frequency": games / continuation_games if continuation_games else None,
                "white_wins": row.get("white"),
                "draws": row.get("draws"),
                "black_wins": row.get("black"),
            }
        )
    moves.sort(key=lambda item: (-item["games"], item["san"]))
    return {
        "available": True,
        "source": source,
        "metadata": metadata,
        "position_games": position_games,
        "continuation_games": continuation_games,
        "terminal_games": terminal_games,
        "position_results": {
            "white_wins": position_wdl.get("white"),
            "draws": position_wdl.get("draws"),
            "black_wins": position_wdl.get("black"),
        } if position_wdl is not None else None,
        "frequency_denominator": "continuation_games",
        "moves": moves,
        "limitations": limitations,
    }


def unavailable_distribution(source: str, metadata: dict, reason: str) -> dict:
    """Represent unavailable data without turning unknown values into zeroes."""
    return {
        "available": False,
        "source": source,
        "metadata": metadata,
        "position_games": None,
        "continuation_games": None,
        "terminal_games": None,
        "position_results": None,
        "frequency_denominator": "continuation_games",
        "moves": [],
        "limitations": [reason],
    }
