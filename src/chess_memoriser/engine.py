from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import time

import chess


LEGACY_STOCKFISH = (
    Path.home() / ".local/opt/stockfish/stockfish/stockfish-linux-x86-64-universal"
)


class StockfishError(RuntimeError):
    pass


def _white_pov_score(value: int, turn: chess.Color) -> int:
    """Convert a UCI side-to-move score to a stable White point of view."""
    return value if turn == chess.WHITE else -value


def find_stockfish(configured: Path | None = None) -> Path | None:
    candidates = [
        configured,
        Path(os.environ["STOCKFISH_EXECUTABLE"]) if os.environ.get("STOCKFISH_EXECUTABLE") else None,
        Path(found) if (found := shutil.which("stockfish")) else None,
        LEGACY_STOCKFISH,
    ]
    for candidate in candidates:
        if candidate and candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def _line_san(board: chess.Board, pv: list[chess.Move], plies: int = 12) -> list[str]:
    line_board = board.copy(stack=False)
    result: list[str] = []
    for move in pv[:plies]:
        if move not in line_board.legal_moves:
            break
        result.append(line_board.san(move))
        line_board.push(move)
    return result


def analyse(
    board: chess.Board,
    executable: Path,
    *,
    depth: int = 16,
    multipv: int = 3,
) -> dict:
    if board.is_game_over():
        return {
            "available": True,
            "engine": "Stockfish",
            "depth": depth,
            "multipv": multipv,
            "perspective": "white",
            "perspective_color": "white",
            "position_key": " ".join(board.fen(en_passant="legal").split()[:4]),
            "terminal": True,
            "lines": [],
        }

    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            [str(executable)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        assert process.stdin is not None and process.stdout is not None
        def send(command: str) -> None:
            if process is None or process.poll() is not None:
                raise StockfishError("Stockfish stopped unexpectedly")
            process.stdin.write(command + "\n")
            process.stdin.flush()

        def read_line(deadline: float) -> str:
            if time.monotonic() >= deadline:
                raise StockfishError("Stockfish analysis timed out")
            line = process.stdout.readline()
            if not line:
                raise StockfishError("Stockfish stopped unexpectedly")
            return line.strip()

        send("uci")
        name = "Stockfish"
        deadline = time.monotonic() + 10
        while True:
            line = read_line(deadline)
            if line.startswith("id name "):
                name = line[8:]
            if line == "uciok":
                break
        for option, value in (("Threads", 1), ("Hash", 64), ("MultiPV", multipv)):
            send(f"setoption name {option} value {value}")
        send("isready")
        deadline = time.monotonic() + 10
        while read_line(deadline) != "readyok":
            pass

        send(f"position fen {board.fen(en_passant='fen')}")
        send(f"go depth {depth}")
        raw_lines: dict[int, dict] = {}
        deadline = time.monotonic() + 120
        while True:
            line = read_line(deadline)
            if line.startswith("bestmove "):
                break
            if not line.startswith("info ") or " score " not in line or " pv " not in line:
                continue
            fields = line.split()
            try:
                rank = int(fields[fields.index("multipv") + 1]) if "multipv" in fields else 1
                line_depth = int(fields[fields.index("depth") + 1])
                score_index = fields.index("score")
                score_unit = fields[score_index + 1]
                score_value = int(fields[score_index + 2])
                pv_index = fields.index("pv")
                pv = [chess.Move.from_uci(value) for value in fields[pv_index + 1:]]
                if not pv:
                    continue
                raw_lines[rank] = {
                    "unit": score_unit,
                    "value": score_value,
                    "depth": line_depth,
                    "seldepth": int(fields[fields.index("seldepth") + 1]) if "seldepth" in fields else None,
                    "nodes": int(fields[fields.index("nodes") + 1]) if "nodes" in fields else None,
                    "pv": pv,
                }
            except (ValueError, IndexError):
                continue
    except OSError as exc:
        raise StockfishError(f"Could not start Stockfish: {exc}") from None
    finally:
        if process is not None and process.poll() is None:
            try:
                assert process.stdin is not None
                process.stdin.write("quit\n")
                process.stdin.flush()
                process.wait(timeout=2)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                process.kill()
                process.wait()
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
            if process.stdout is not None:
                process.stdout.close()

    lines = []
    for rank, info in sorted(raw_lines.items()):
        pv = info["pv"]
        # UCI scores are relative to the side to move. The interface uses the
        # conventional fixed White point of view, so Black-to-move values need
        # their sign reversed. This applies equally to centipawn and mate scores.
        evaluation = {
            "unit": info["unit"],
            "value": _white_pov_score(info["value"], board.turn),
        }
        lines.append(
            {
                "rank": rank,
                "evaluation": evaluation,
                "first_move_uci": pv[0].uci(),
                "first_move_san": board.san(pv[0]),
                "san": _line_san(board, pv),
                "depth": info["depth"],
                "seldepth": info["seldepth"],
                "nodes": info["nodes"],
            }
        )
    return {
        "available": True,
        "engine": name,
        "depth": max((line["depth"] or 0 for line in lines), default=depth),
        "multipv": multipv,
        "perspective": "white",
        "perspective_color": "white",
        "position_key": " ".join(board.fen(en_passant="legal").split()[:4]),
        "terminal": False,
        "lines": lines,
    }
