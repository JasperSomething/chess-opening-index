import unittest

from chess_memoriser.position import from_uci_sequence
from chess_memoriser.service import position_state


class PositionStateTests(unittest.TestCase):
    def test_state_is_database_free_and_complete_for_board_rendering(self):
        state = position_state(from_uci_sequence(("e2e4", "e7e5", "g1f3")))
        self.assertEqual(state["position"]["turn"], "black")
        self.assertEqual(state["position"]["san_sequence"], ["e4", "e5", "Nf3"])
        self.assertTrue(state["legal_moves"])
        self.assertNotIn("distributions", state)


if __name__ == "__main__":
    unittest.main()
