from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import struct

import chess

from chess_memoriser.result import distribution


def compact_key(board: chess.Board) -> bytes:
    """Lossless key used by the old project's complete 2200+ index."""
    rights = board.clean_castling_rights()
    flags = int(board.turn) << 4
    for index, square in enumerate((chess.H1, chess.A1, chess.H8, chess.A8)):
        if rights & chess.BB_SQUARES[square]:
            flags |= 1 << index
    return struct.pack(
        "<4QBB",
        board.pawns | board.bishops | board.queens,
        board.knights | board.bishops | board.kings,
        board.rooks | board.queens | board.kings,
        board.occupied_co[chess.WHITE],
        flags,
        board.ep_square if board.has_legal_en_passant() else 64,
    )


def decode_move(code: int) -> chess.Move:
    return chess.Move(code & 63, (code >> 6) & 63, promotion=(code >> 12) or None)


class MasterDatabaseError(RuntimeError):
    pass


class MasterDatabaseAdapter:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise MasterDatabaseError(f"Master database not found: {self.path}")
        try:
            self.db = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, timeout=30)
            state_row = self.db.execute("SELECT value FROM state WHERE id=1").fetchone()
            self.state = json.loads(state_row[0]) if state_row else None
            self.db.execute("SELECT 1 FROM edges LIMIT 1").fetchone()
        except (sqlite3.Error, json.JSONDecodeError) as exc:
            raise MasterDatabaseError(f"Unsupported master database: {exc}") from None
        if not self.state or self.state.get("phase") != "complete" or self.state.get("sample"):
            raise MasterDatabaseError("Master database is not a completed full index")
        source = self.state.get("input", {})
        if source.get("minimum_rating") != 2200:
            raise MasterDatabaseError("Master database is not the expected both-players-2200+ population")

    def query(self, board: chess.Board) -> dict:
        rows = self.db.execute(
            "SELECT move,white,draws,black FROM edges WHERE position=?",
            (compact_key(board),),
        ).fetchall()
        moves: list[dict] = []
        terminal = {"white": 0, "draws": 0, "black": 0}
        position = {"white": 0, "draws": 0, "black": 0}
        for move_code, white, draws, black in rows:
            counts = {"white": white, "draws": draws, "black": black}
            for name in position:
                position[name] += counts[name]
            if move_code == 0:
                terminal = counts
            else:
                move = decode_move(move_code)
                if move not in board.legal_moves:
                    raise MasterDatabaseError(f"Index returned illegal move {move.uci()} for queried position")
                moves.append({"uci": move.uci(), **counts})

        input_meta = self.state["input"]
        result = distribution(
            board,
            source="installed_master_database",
            metadata={
                "adapter": "lumbra_complete_2200_v1",
                "database": str(self.path),
                "population": "Lumbra GigaBase records where both WhiteElo and BlackElo are at least 2200",
                "minimum_rating_both_players": 2200,
                "database_complete": True,
                "source_games_scanned": self.state.get("games"),
                "accepted_master_games": self.state.get("accepted"),
                "source_pgn_bytes": input_meta.get("bytes"),
                "source_release": "2026-07-08",
                "source_type": "publisher-assembled OTB PGN collection; not Lichess games",
                "valid_header_date_range": "1749-2026",
                "dated_records_in_valid_range": 10353323,
                "undated_or_implausibly_dated_records": 2165,
            },
            position_wdl=position,
            move_rows=moves,
            limitations=[
                "Publisher records are not independently deduplicated.",
                "Games with missing/non-numeric ratings are excluded; both players must be rated 2200+.",
                "Standard-start games with known results only; each game contributes once per position using its first continuation.",
                "The publisher's collection includes some correspondence, rapid, and blitz-labelled records.",
                "The 2200 threshold uses PGN WhiteElo/BlackElo headers, not verified titles or a Lichess rating bucket.",
            ],
        )
        # The zero edge is independently useful for auditing the derived terminal count.
        assert result["terminal_games"] == sum(terminal.values())
        return result

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "MasterDatabaseAdapter":
        return self

    def __exit__(self, *_args) -> None:
        self.close()
