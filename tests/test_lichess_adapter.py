import tempfile
import unittest
from pathlib import Path

import chess

from chess_memoriser.adapters.lichess import LichessAdapter, LichessFilters
from chess_memoriser.cache import ResponseCache


class LichessAdapterTests(unittest.TestCase):
    def test_standard_castling_is_normalized_from_explorer_uci(self):
        board = chess.Board()
        for san in "e4 e5 Nf3 Nc6 Bc4 Bc5".split():
            board.push_san(san)
        payload = {
            "white": 6,
            "draws": 3,
            "black": 1,
            "moves": [{"uci": "e1h1", "white": 6, "draws": 3, "black": 1}],
        }
        LichessAdapter._validate(board, payload)
        with tempfile.TemporaryDirectory() as directory:
            with ResponseCache(Path(directory) / "cache.sqlite") as cache:
                cache.put("lichess", " ".join(board.fen(en_passant="legal").split()[:4]), LichessFilters().key, "test", payload)
                result = LichessAdapter(cache, filters=LichessFilters()).query(board, offline=True)
        self.assertEqual(result["moves"][0]["uci"], "e1g1")
        self.assertEqual(result["moves"][0]["san"], "O-O")


if __name__ == "__main__":
    unittest.main()
