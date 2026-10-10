from __future__ import annotations

import argparse
import json
from pathlib import Path

import chess

from chess_memoriser.adapters.master import MasterDatabaseAdapter
from chess_memoriser.config import DEFAULT_MASTER_DB, PROJECT_ROOT
from chess_memoriser.opening_guides import catalogue_response
from chess_memoriser.position import from_uci_sequence, position_key


MIN_CONTINUATIONS = 75
MAX_PLIES = 28
BRANCH_FREQUENCY = 0.15
DOMINANT_FREQUENCY = 0.50
SECOND_MOVE_FREQUENCY = 0.30


def pgn(sans: list[str]) -> str:
    parts = []
    for index, san in enumerate(sans):
        parts.append(f"{index // 2 + 1}. {san}" if index % 2 == 0 else san)
    return " ".join(parts) if parts else "Starting position"


def hierarchy_nodes(roots: list[dict]):
    def visit(node: dict, path: tuple[str, ...]):
        current = (*path, node["label"])
        yield current, node
        for child in node["children"]:
            yield from visit(child, current)
    for root in roots:
        yield from visit(root, ())


def build(master_db: Path) -> dict:
    hierarchy = catalogue_response()["hierarchy_draft"]
    query_cache: dict[str, dict] = {}
    entries = {}
    with MasterDatabaseAdapter(master_db) as masters:
        for path, node in hierarchy_nodes(hierarchy["roots"]):
            board = chess.Board(node["position_data"]["fen"])
            ucis = list(node["position_data"]["moves_uci"])
            sans = list(node["position_data"]["moves_san"])
            stop_reason = "middlegame_depth"
            stop_games = None
            alternatives = []
            while len(ucis) < MAX_PLIES:
                key = position_key(board)
                result = query_cache.get(key)
                if result is None:
                    result = masters.query(board)
                    query_cache[key] = result
                stop_games = result["continuation_games"]
                moves = result["moves"]
                alternatives = [
                    {"san": move["san"], "games": move["games"], "frequency": move["frequency"]}
                    for move in moves[:5]
                ]
                if not moves:
                    stop_reason = "no_continuations"
                    break
                if stop_games < MIN_CONTINUATIONS:
                    stop_reason = "small_sample"
                    break
                meaningful = [move for move in moves if (move["frequency"] or 0) >= BRANCH_FREQUENCY]
                second = moves[1]["frequency"] if len(moves) > 1 else 0
                if (moves[0]["frequency"] or 0) < DOMINANT_FREQUENCY or len(meaningful) >= 3 or second >= SECOND_MOVE_FREQUENCY:
                    stop_reason = "wide_choice"
                    break
                move = chess.Move.from_uci(moves[0]["uci"])
                sans.append(board.san(move))
                ucis.append(move.uci())
                board.push(move)
            entries["/".join(path)] = {
                "definition_position_key": node["position_data"]["position_key"],
                "moves_san": sans,
                "moves_uci": ucis,
                "pgn": pgn(sans),
                "fen": board.fen(en_passant="legal"),
                "position_key": position_key(board),
                "stop_reason": stop_reason,
                "continuation_games_at_stop": stop_games,
                "choices_at_stop": alternatives,
            }
    return {
        "version": 1,
        "source": "installed local Lumbra OTB index; both players rated 2200+",
        "method": {
            "minimum_continuation_games": MIN_CONTINUATIONS,
            "maximum_plies": MAX_PLIES,
            "wide_choice": f"the leading move is below {DOMINANT_FREQUENCY:.0%}, at least three moves reach {BRANCH_FREQUENCY:.0%}, or the runner-up reaches {SECOND_MOVE_FREQUENCY:.0%}",
            "selection": "Continue only along a majority local-OTB trunk; stop before choosing among plural alternatives. Frequencies are conditional at each position, and no complete-line probability or theoretical-best claim is made.",
        },
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master-db", type=Path, default=DEFAULT_MASTER_DB)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "opening_hierarchy_mainlines.json")
    args = parser.parse_args()
    payload = build(args.master_db)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(payload['entries'])} hierarchy mainlines to {args.output}")


if __name__ == "__main__":
    main()
