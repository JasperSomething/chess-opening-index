from __future__ import annotations

from dataclasses import dataclass
import re

import chess


class PositionError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedPosition:
    board: chess.Board
    input_kind: str
    original_input: str
    san_sequence: tuple[str, ...]
    uci_sequence: tuple[str, ...]

    @property
    def key(self) -> str:
        return position_key(self.board)

    def as_dict(self) -> dict:
        return {
            "input_kind": self.input_kind,
            "input": self.original_input,
            "fen": self.board.fen(en_passant="legal"),
            "position_key": self.key,
            "turn": "white" if self.board.turn else "black",
            "san_sequence": list(self.san_sequence),
            "uci_sequence": list(self.uci_sequence),
        }


def position_key(board: chess.Board) -> str:
    """FEN identity used by Lichess and the legacy cache (no move counters)."""
    return " ".join(board.fen(en_passant="legal").split()[:4])


def board_from_key(key: str) -> chess.Board:
    return chess.Board(f"{key} 0 1")


def _san_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in text.replace("\n", " ").split():
        token = re.sub(r"^\d+\.(?:\.\.)?", "", raw.strip())
        if not token or token in {"*", "1-0", "0-1", "1/2-1/2"}:
            continue
        tokens.append(token)
    return tokens


def from_san(text: str) -> ParsedPosition:
    board = chess.Board()
    sans: list[str] = []
    ucis: list[str] = []
    for ply, token in enumerate(_san_tokens(text), 1):
        try:
            move = board.parse_san(token)
        except ValueError as exc:
            raise PositionError(f"Illegal or invalid SAN at ply {ply}: {token!r} ({exc})") from None
        sans.append(board.san(move))
        ucis.append(move.uci())
        board.push(move)
    return ParsedPosition(board, "san", text, tuple(sans), tuple(ucis))


def from_fen(text: str) -> ParsedPosition:
    try:
        board = chess.Board(text)
    except ValueError as exc:
        raise PositionError(f"Invalid FEN: {exc}") from None
    if not board.is_valid():
        raise PositionError("FEN does not describe a valid standard-chess position")
    return ParsedPosition(board, "fen", text, (), ())


def from_uci_sequence(moves: list[str] | tuple[str, ...]) -> ParsedPosition:
    board = chess.Board()
    sans: list[str] = []
    ucis: list[str] = []
    for ply, uci in enumerate(moves, 1):
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            raise PositionError(f"Invalid UCI at ply {ply}: {uci!r}") from None
        if move not in board.legal_moves:
            raise PositionError(f"Illegal UCI at ply {ply}: {uci!r}")
        sans.append(board.san(move))
        ucis.append(move.uci())
        board.push(move)
    original = ",".join(moves)
    return ParsedPosition(board, "uci", original, tuple(sans), tuple(ucis))


def parse_position(*, moves: str | None = None, fen: str | None = None) -> ParsedPosition:
    if (moves is None) == (fen is None):
        raise PositionError("Supply exactly one of --moves or --fen")
    return from_san(moves) if moves is not None else from_fen(fen or "")
