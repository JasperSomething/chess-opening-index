import unittest

from chess_memoriser.opening_guides import catalogue_response, guide_response, opening_data


class OpeningGuideTests(unittest.TestCase):
    def test_catalogue_has_validated_365_starting_families(self):
        payload = catalogue_response()
        self.assertEqual(len(payload["openings"]), 45)
        self.assertEqual(sum(bool(item["guide_available"]) for item in payload["openings"]), 3)

    def test_catalogue_taxonomy_separates_major_families(self):
        payload = catalogue_response()
        openings = {item["slug"]: item for item in payload["openings"]}
        self.assertEqual(openings["queens-gambit"]["catalogue_role"], "umbrella")
        self.assertEqual(openings["slav-defense"]["family"], "slav-family")
        self.assertEqual(openings["queens-gambit-declined"]["family"], "qgd-family")
        self.assertEqual(openings["queens-gambit-accepted"]["family"], "qga-and-sidelines")
        self.assertEqual(openings["italian-game"]["family"], "e4-e5")
        self.assertEqual(openings["scandinavian-defense"]["family"], "other-e4")
        self.assertEqual(openings["birds-opening"]["section"], "bird-dutch")
        self.assertEqual(openings["dutch-defense"]["section"], "bird-dutch")
        english = {openings[slug]["family"] for slug in (
            "english-reversed-sicilian", "english-symmetrical", "english-neo-catalan"
        )}
        self.assertEqual(english, {"english-main"})

    def test_user_hierarchy_draft_is_preserved_and_linked(self):
        hierarchy = catalogue_response()["hierarchy_draft"]
        self.assertEqual([root["label"] for root in hierarchy["roots"]], [
            "e4", "d4", "c4 (English)", "Alternatives/ Sidelines/ Other"
        ])
        e4 = hierarchy["roots"][0]
        self.assertEqual([item["label"] for item in e4["children"]], [
            "e5", "Sicilian", "French", "Caro-Kann", "Alternatives"
        ])
        sicilian = e4["children"][1]
        self.assertEqual([item["label"] for item in sicilian["children"]], [
            "d6 open", "e6 open", "Nc6 open", "Closed", "Alternatives"
        ])
        qg = opening_data()["hierarchy_draft"]["roots"][1]["children"][1]
        self.assertEqual(qg["opening_slugs"], ["queens-gambit"])
        self.assertEqual(qg["children"][0]["opening_slugs"], ["queens-gambit-accepted"])

    def test_every_hierarchy_card_has_a_valid_pgn_position(self):
        hierarchy = catalogue_response()["hierarchy_draft"]
        nodes = []
        def collect(node):
            nodes.append(node)
            for child in node["children"]:
                collect(child)
        for root in hierarchy["roots"]:
            collect(root)
        self.assertEqual(len(nodes), 112)
        self.assertTrue(all(node["pgn"] for node in nodes))
        self.assertTrue(all(node["position_data"]["fen"] for node in nodes))
        najdorf = next(node for node in nodes if node["label"] == "Najdorf")
        self.assertEqual(najdorf["position_data"]["moves_san"][-1], "a6")
        jobava = next(node for node in nodes if node["label"] == "Jobava London")
        self.assertEqual(jobava["position_data"]["moves_san"][-1], "Bf4")

    def test_e6_scheveningen_plays_knight_before_d6(self):
        e4 = catalogue_response()["hierarchy_draft"]["roots"][0]
        sicilian = next(node for node in e4["children"] if node["label"] == "Sicilian")
        d6_open = next(node for node in sicilian["children"] if node["label"] == "d6 open")
        e6_open = next(node for node in sicilian["children"] if node["label"] == "e6 open")
        direct = next(node for node in d6_open["children"] if node["label"] == "Scheveningen")
        anti_maroczy = next(node for node in e6_open["children"] if node["label"] == "Scheveningen")
        self.assertEqual(
            anti_maroczy["position_data"]["moves_san"],
            ["e4", "c5", "Nf3", "e6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "d6"],
        )
        self.assertLess(
            anti_maroczy["position_data"]["moves_san"].index("Nf6"),
            anti_maroczy["position_data"]["moves_san"].index("d6"),
        )
        self.assertEqual(
            anti_maroczy["position_data"]["position_key"],
            direct["position_data"]["position_key"],
        )

    def test_hierarchy_mainlines_extend_definitions_and_explain_the_stop(self):
        hierarchy = catalogue_response()["hierarchy_draft"]
        nodes = []
        def collect(node):
            nodes.append(node)
            for child in node["children"]:
                collect(child)
        for root in hierarchy["roots"]:
            collect(root)
        for node in nodes:
            definition = node["position_data"]["moves_uci"]
            mainline = node["mainline_position_data"]["moves_uci"]
            self.assertEqual(mainline[:len(definition)], definition)
            self.assertIn(node["mainline_stop_reason"], {
                "wide_choice", "small_sample", "middlegame_depth", "no_continuations"
            })
        self.assertGreaterEqual(sum(
            len(node["mainline_position_data"]["moves_uci"]) > len(node["position_data"]["moves_uci"])
            for node in nodes
        ), 50)
        ruy = next(node for node in nodes if node["label"] == "Ruy Lopez")
        self.assertIn("O-O", ruy["mainline_position_data"]["moves_san"])
        self.assertTrue(ruy["mainline_choices"])

    def test_kings_gambit_source_error_is_corrected(self):
        opening = next(item for item in opening_data()["openings"] if item["slug"] == "kings-gambit")
        self.assertEqual(opening["moves_san"], ["e4", "e5", "f4"])
        self.assertEqual(opening["eco"], ["C30"])
        self.assertIn("corrected", opening["source_correction"])

    def test_three_pilots_cover_both_sides(self):
        for slug in ("scandinavian-defense", "italian-game", "queens-gambit"):
            guide = guide_response(slug)
            self.assertIsNotNone(guide)
            self.assertEqual({decision["side"] for decision in guide["decisions"]}, {"White", "Black"})
            self.assertGreaterEqual(len(guide["lines"]), 7)

    def test_guide_choices_have_exact_legal_moves_and_positions(self):
        for guide in opening_data()["guides"].values():
            for decision in guide["decisions"]:
                self.assertTrue(decision["position_data"]["position_key"])
                for option in decision["options"]:
                    self.assertEqual(option["line_uci"][-1], option["move_uci"])
                    self.assertTrue(option["target_position_key"])

    def test_italian_alternate_order_reaches_same_position(self):
        opening = next(item for item in opening_data()["openings"] if item["slug"] == "italian-game")
        self.assertTrue(opening["alternate_move_orders"][0]["same_defining_position"])

    def test_low_otb_practical_choices_are_marked_for_compact_display(self):
        guide = guide_response("scandinavian-defense")
        compact = [
            option
            for decision in guide["decisions"]
            for option in decision["options"]
            if option.get("prominence") == "practical_sideline"
        ]
        self.assertEqual({option["move"] for option in compact}, {"e5", "c6"})
        self.assertTrue(all(option["otb_reference_frequency"] < 0.01 for option in compact))

    def test_scandinavian_primary_line_is_the_named_qa5_main_line(self):
        guide = guide_response("scandinavian-defense")
        primary = [line for line in guide["lines"] if line.get("primary")]
        self.assertEqual(len(primary), 1)
        self.assertEqual(
            primary[0]["position_data"]["moves_san"][:8],
            ["e4", "d5", "exd5", "Qxd5", "Nc3", "Qa5", "d4", "Nf6"],
        )
        self.assertEqual(primary[0]["position_data"]["moves_san"][-4:], ["Bd2", "e6", "Nd5", "Qd8"])


if __name__ == "__main__":
    unittest.main()
