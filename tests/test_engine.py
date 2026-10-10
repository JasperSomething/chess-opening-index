import unittest

import chess

from chess_memoriser.engine import analyse, find_stockfish


class StockfishTests(unittest.TestCase):
    def test_installed_stockfish_returns_legal_multipv(self):
        executable = find_stockfish()
        if executable is None:
            self.skipTest("Stockfish is not installed")
        board = chess.Board()
        result = analyse(board, executable, depth=8, multipv=2)
        self.assertEqual(result["perspective"], "side_to_move")
        self.assertEqual(result["perspective_color"], "white")
        self.assertEqual(result["position_key"], "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -")
        self.assertEqual(len(result["lines"]), 2)
        for line in result["lines"]:
            self.assertIn(chess.Move.from_uci(line["first_move_uci"]), board.legal_moves)
            self.assertTrue(line["san"])
            self.assertIn(line["evaluation"]["unit"], ("cp", "mate"))

    def test_terminal_position_does_not_start_search(self):
        executable = find_stockfish()
        if executable is None:
            self.skipTest("Stockfish is not installed")
        board = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        result = analyse(board, executable, depth=8, multipv=3)
        self.assertTrue(result["terminal"])
        self.assertEqual(result["lines"], [])

    def test_black_to_move_uses_black_perspective(self):
        executable = find_stockfish()
        if executable is None:
            self.skipTest("Stockfish is not installed")
        board = chess.Board()
        board.push_san("e4")
        result = analyse(board, executable, depth=8, multipv=1)
        self.assertEqual(result["perspective"], "side_to_move")
        self.assertEqual(result["perspective_color"], "black")
        self.assertTrue(result["position_key"].endswith(" b KQkq -"))
        self.assertIn(chess.Move.from_uci(result["lines"][0]["first_move_uci"]), board.legal_moves)


if __name__ == "__main__":
    unittest.main()
