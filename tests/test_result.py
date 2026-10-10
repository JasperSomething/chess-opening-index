import unittest

import chess

from chess_memoriser.result import distribution, unavailable_distribution


class ResultTests(unittest.TestCase):
    def test_frequency_uses_all_continuations_not_position_total(self):
        data = distribution(
            chess.Board(),
            source="test",
            metadata={},
            position_wdl={"white": 6, "draws": 3, "black": 1},
            move_rows=[
                {"uci": "e2e4", "white": 3, "draws": 1, "black": 1},
                {"uci": "d2d4", "white": 2, "draws": 1, "black": 0},
            ],
            limitations=[],
        )
        self.assertEqual(data["position_games"], 10)
        self.assertEqual(data["continuation_games"], 8)
        self.assertEqual(data["terminal_games"], 2)
        self.assertEqual(data["moves"][0]["frequency"], 5 / 8)

    def test_unavailable_is_not_zero(self):
        data = unavailable_distribution("test", {}, "offline")
        self.assertFalse(data["available"])
        self.assertIsNone(data["position_games"])
        self.assertIsNone(data["continuation_games"])


if __name__ == "__main__":
    unittest.main()
