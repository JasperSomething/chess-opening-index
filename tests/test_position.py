import unittest

import chess

from chess_memoriser.position import PositionError, from_fen, from_san, from_uci_sequence, position_key


class PositionTests(unittest.TestCase):
    def test_san_sequence(self):
        parsed = from_san("1. e4 e5 2. Nf3")
        self.assertEqual(parsed.uci_sequence, ("e2e4", "e7e5", "g1f3"))
        self.assertEqual(parsed.san_sequence, ("e4", "e5", "Nf3"))

    def test_transposition_key(self):
        a = from_san("Nf3 Nf6 g3 g6")
        b = from_san("g3 g6 Nf3 Nf6")
        self.assertEqual(a.key, b.key)

    def test_legal_en_passant_identity(self):
        board = chess.Board()
        board.push_san("e4")
        # e3 is not legally capturable and is omitted from the canonical key.
        self.assertEqual(position_key(board).split()[3], "-")

    def test_bad_san(self):
        with self.assertRaises(PositionError):
            from_san("e4 e5 e4")

    def test_fen(self):
        parsed = from_fen(chess.STARTING_FEN)
        self.assertEqual(parsed.key, position_key(chess.Board()))

    def test_uci_sequence_for_gui(self):
        parsed = from_uci_sequence(("e2e4", "e7e5", "g1f3"))
        self.assertEqual(parsed.san_sequence, ("e4", "e5", "Nf3"))


if __name__ == "__main__":
    unittest.main()
