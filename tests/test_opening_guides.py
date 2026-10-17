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
            "Najdorf", "Classical", "Dragon", "Scheveningen", "4 Knights",
            "Moscow variation", "Kan", "Taimanov", "Rossolimo", "Sveshnikov",
            "Closed", "Alapin", "O-Kelly Variation", "Nimsowitsch variation",
            "Katalimov variation",
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
        self.assertEqual(len(nodes), 129)
        self.assertTrue(all(node["pgn"] for node in nodes))
        self.assertTrue(all(node["position_data"]["fen"] for node in nodes))
        najdorf = next(node for node in nodes if node["label"] == "Najdorf")
        self.assertEqual(najdorf["position_data"]["moves_san"][-1], "a6")
        jobava = next(node for node in nodes if node["label"] == "Jobava London")
        self.assertEqual(jobava["position_data"]["moves_san"][-1], "Bf4")

    def test_opening_wiki_is_attached_to_valid_taxonomy_paths(self):
        payload = catalogue_response()
        self.assertEqual(payload["wiki"]["home"]["title"], "Opening theory map")
        self.assertIn("e4/Sicilian", payload["wiki"]["entries"])
        self.assertIn("d4/Queen's Gambit", payload["wiki"]["entries"])
        self.assertIn("c4 (English)", payload["wiki"]["entries"])
        for article in [payload["wiki"]["home"], *payload["wiki"]["entries"].values()]:
            self.assertTrue(article["summary"])
            self.assertTrue(all(source["url"].startswith("https://") for source in article.get("sources", [])))

    def test_sicilian_families_are_merged_into_key_positions(self):
        e4 = catalogue_response()["hierarchy_draft"]["roots"][0]
        sicilian = next(node for node in e4["children"] if node["label"] == "Sicilian")
        families = {node["label"]: node for node in sicilian["children"]}
        self.assertTrue(all(node["level"] == "family" for node in families.values()))
        self.assertNotIn("Kupreichik variation", families)
        self.assertTrue({"d6 open", "e6 open", "Nc6 open", "Alternatives"}.isdisjoint(families))

        dragon = families["Dragon"]
        self.assertEqual(dragon["child_role"], "key_positions")
        self.assertEqual([node["label"] for node in dragon["children"]], [
            "Dragon Sicilian", "Hyper Accelerated Dragon", "Accelerated Dragon"
        ])
        traditional = dragon["children"][0]
        self.assertEqual(traditional["child_role"], "key_positions")
        self.assertEqual(
            [node["label"] for node in traditional["children"]],
            ["Yugoslav Approach"],
        )
        traditional_yugoslav = traditional["children"][0]
        self.assertEqual(
            traditional_yugoslav["position_data"]["moves_san"],
            [
                "e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6",
                "Nc3", "g6", "Be3", "Bg7", "f3", "O-O", "Qd2", "Nc6",
                "Bc4", "Bd7", "O-O-O",
            ],
        )
        hyper = dragon["children"][1]
        self.assertEqual(hyper["child_role"], "key_positions")
        self.assertEqual(
            [node["label"] for node in hyper["children"]],
            ["Maroczy Approach", "Yugoslav Approach"],
        )
        hyper_maroczy, hyper_yugoslav = hyper["children"]
        self.assertEqual(
            hyper_maroczy["position_data"]["moves_san"],
            [
                "e4", "c5", "Nf3", "g6", "d4", "cxd4", "Nxd4", "Bg7",
                "c4", "Nc6", "Be3", "Nf6", "Nc3", "O-O", "Be2", "d6",
                "O-O", "Bd7",
            ],
        )
        self.assertEqual(len(hyper_maroczy["sidelines"]), 1)
        self.assertEqual(
            hyper_maroczy["sidelines"][0]["position_data"]["moves_san"][-4:],
            ["Ng4", "Qxg4", "Nxd4", "Qd1"],
        )
        self.assertEqual(
            hyper_yugoslav["position_data"]["moves_san"],
            [
                "e4", "c5", "Nf3", "g6", "d4", "cxd4", "Nxd4", "Bg7",
                "Nc3", "Nc6", "Be3", "Nf6", "Bc4", "O-O", "Bb3", "d6",
                "f3", "Bd7", "Qd2",
            ],
        )
        accelerated = dragon["children"][2]
        self.assertEqual(accelerated["child_role"], "key_positions")
        self.assertEqual([node["label"] for node in accelerated["children"]], [
            "Maroczy Approach", "Yugoslav Approach"
        ])
        maroczy, yugoslav = accelerated["children"]
        self.assertEqual(
            maroczy["position_data"]["moves_san"][-10:],
            ["c4", "Bg7", "Be3", "Nf6", "Nc3", "O-O", "Be2", "d6", "O-O", "Bd7"],
        )
        self.assertEqual(len(maroczy["sidelines"]), 1)
        self.assertEqual(
            maroczy["sidelines"][0]["position_data"]["moves_san"][-4:],
            ["Ng4", "Qxg4", "Nxd4", "Qd1"],
        )
        self.assertEqual(
            yugoslav["position_data"]["moves_san"][-11:],
            ["Nc3", "Bg7", "Be3", "Nf6", "Bc4", "O-O", "Bb3", "d6", "f3", "Bd7", "Qd2"],
        )
        self.assertEqual(
            traditional_yugoslav["position_data"]["moves_san"][:10],
            ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "g6"],
        )
        self.assertEqual(
            yugoslav["position_data"]["moves_san"][:8],
            ["e4", "c5", "Nf3", "Nc6", "d4", "cxd4", "Nxd4", "g6"],
        )
        self.assertEqual(
            hyper_yugoslav["position_data"]["moves_san"][:8],
            ["e4", "c5", "Nf3", "g6", "d4", "cxd4", "Nxd4", "Bg7"],
        )

        najdorf = families["Najdorf"]
        self.assertEqual(najdorf["child_role"], "key_positions")
        self.assertEqual(
            [node["label"] for node in najdorf["children"]],
            [
                "English Attack", "Opocensky Variation", "Adams Attack",
                "Lipnitsky Attack", "Amsterdam Variation", "Zagreb Variation",
            ],
        )
        self.assertEqual(
            [node["position_data"]["moves_san"][-1] for node in najdorf["children"]],
            ["Be3", "Be2", "h3", "Bc4", "f4", "g3"],
        )

        scheveningen = families["Scheveningen"]
        self.assertEqual(scheveningen["child_role"], "key_positions")
        self.assertEqual([node["label"] for node in scheveningen["children"]], [
            "Nf6 before d6", "Direct d6 Move Order"
        ])
        anti_maroczy, direct = scheveningen["children"]
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

        four_knights = families["4 Knights"]
        self.assertEqual([node["label"] for node in four_knights["children"]], [
            "e6 Move Order", "Nc6 Move Order"
        ])
        self.assertEqual(
            four_knights["children"][0]["position_data"]["position_key"],
            four_knights["children"][1]["position_data"]["position_key"],
        )

        sveshnikov = families["Sveshnikov"]
        self.assertEqual([node["label"] for node in sveshnikov["children"]], [
            "Bg5 Mainline", "Bxf6 gxf6 Line", "Early 7.Nd5 Line",
            "Kalashnikov Sideline",
        ])
        bg5, doubled, early_nd5, kalashnikov = sveshnikov["children"]
        self.assertEqual(
            bg5["position_data"]["moves_san"][-8:],
            ["Bg5", "a6", "Na3", "b5", "Nd5", "Be7", "Bxf6", "Bxf6"],
        )
        self.assertEqual(bg5["child_role"], "key_positions")
        self.assertEqual(
            [node["label"] for node in bg5["children"]],
            ["11.c4 Branch", "11.c3 Branch"],
        )
        c4_branch, c3_branch = bg5["children"]
        self.assertEqual(c4_branch["position_data"]["moves_san"][-3:], ["c4", "b4", "Nc2"])
        self.assertEqual(
            c3_branch["position_data"]["moves_san"][-12:],
            ["c3", "O-O", "Nc2", "Bg5", "a4", "bxa4", "Rxa4", "a5", "Bc4", "Rb8", "b3", "Kh8"],
        )
        self.assertEqual(doubled["position_data"]["moves_san"][-2:], ["Bxf6", "gxf6"])
        self.assertEqual(early_nd5["position_data"]["moves_san"][-4:], ["Nd5", "Nxd5", "exd5", "Nb8"])
        self.assertEqual(
            kalashnikov["position_data"]["moves_san"],
            ["e4", "c5", "Nf3", "Nc6", "d4", "cxd4", "Nxd4", "e5", "Nb5", "d6"],
        )
        alapin = families["Alapin"]
        self.assertEqual([node["label"] for node in alapin["children"]], [
            "Alapin", "Delayed Alapin Transposition"
        ])

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
