from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from chess_memoriser.config import PROJECT_ROOT
from chess_memoriser.position import ParsedPosition, from_san, from_uci_sequence


CATALOGUE_PATH = PROJECT_ROOT / "data" / "opening_catalogue.json"
GUIDES_PATH = PROJECT_ROOT / "data" / "pilot_guides.json"
HIERARCHY_PATH = PROJECT_ROOT / "data" / "opening_hierarchy_draft.txt"
HIERARCHY_MAINLINES_PATH = PROJECT_ROOT / "data" / "opening_hierarchy_mainlines.json"
WIKI_PATH = PROJECT_ROOT / "data" / "opening_wiki.json"

KEY_POSITION_FAMILIES = {
    "e4/Sicilian/Classical",
    "e4/Sicilian/Najdorf",
    "e4/Sicilian/Dragon",
    "e4/Sicilian/Scheveningen",
    "e4/Sicilian/4 Knights",
    "e4/Sicilian/Sveshnikov",
    "e4/Sicilian/Sveshnikov/Bg5 Mainline",
    "e4/Sicilian/Alapin",
    "e4/Sicilian/Dragon/Dragon Sicilian",
    "e4/Sicilian/Dragon/Hyper Accelerated Dragon",
    "e4/Sicilian/Dragon/Accelerated Dragon",
}

HIERARCHY_POSITION_GROUPS = {
    "e4/Sicilian/Najdorf": [
        {
            "label": "English Attack",
            "line": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be3",
            "sidelines": [],
        },
        {
            "label": "Opocensky Variation",
            "line": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be2",
            "sidelines": [],
        },
        {
            "label": "Adams Attack",
            "line": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. h3",
            "sidelines": [],
        },
        {
            "label": "Lipnitsky Attack",
            "line": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Bc4",
            "sidelines": [],
        },
        {
            "label": "Amsterdam Variation",
            "line": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. f4",
            "sidelines": [],
        },
        {
            "label": "Zagreb Variation",
            "line": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. g3",
            "sidelines": [],
        },
    ],
    "e4/Sicilian/Sveshnikov": [
        {
            "label": "Bg5 Mainline",
            "line": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e5 6. Ndb5 d6 7. Bg5 a6 8. Na3 b5 9. Nd5 Be7 10. Bxf6 Bxf6",
            "sidelines": [],
            "children": [
                {
                    "label": "11.c4 Branch",
                    "line": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e5 6. Ndb5 d6 7. Bg5 a6 8. Na3 b5 9. Nd5 Be7 10. Bxf6 Bxf6 11. c4 b4 12. Nc2",
                    "sidelines": [],
                },
                {
                    "label": "11.c3 Branch",
                    "line": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e5 6. Ndb5 d6 7. Bg5 a6 8. Na3 b5 9. Nd5 Be7 10. Bxf6 Bxf6 11. c3 O-O 12. Nc2 Bg5 13. a4 bxa4 14. Rxa4 a5 15. Bc4 Rb8 16. b3 Kh8",
                    "sidelines": [],
                },
            ],
        },
        {
            "label": "Bxf6 gxf6 Line",
            "line": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e5 6. Ndb5 d6 7. Bg5 a6 8. Na3 b5 9. Bxf6 gxf6",
            "sidelines": [],
        },
        {
            "label": "Early 7.Nd5 Line",
            "line": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e5 6. Ndb5 d6 7. Nd5 Nxd5 8. exd5 Nb8",
            "sidelines": [],
        },
        {
            "label": "Kalashnikov Sideline",
            "line": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 e5 5. Nb5 d6",
            "sidelines": [],
        },
    ],
    "e4/Sicilian/Dragon/Dragon Sicilian": [
        {
            "label": "Yugoslav Approach",
            "line": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6 6. Be3 Bg7 7. f3 O-O 8. Qd2 Nc6 9. Bc4 Bd7 10. O-O-O",
            "sidelines": [],
        },
    ],
    "e4/Sicilian/Dragon/Hyper Accelerated Dragon": [
        {
            "label": "Maroczy Approach",
            "line": "1. e4 c5 2. Nf3 g6 3. d4 cxd4 4. Nxd4 Bg7 5. c4 Nc6 6. Be3 Nf6 7. Nc3 O-O 8. Be2 d6 9. O-O Bd7",
            "sidelines": [
                {
                    "label": "7...Ng4 tactical sideline",
                    "line": "1. e4 c5 2. Nf3 g6 3. d4 cxd4 4. Nxd4 Bg7 5. c4 Nc6 6. Be3 Nf6 7. Nc3 Ng4 8. Qxg4 Nxd4 9. Qd1",
                }
            ],
        },
        {
            "label": "Yugoslav Approach",
            "line": "1. e4 c5 2. Nf3 g6 3. d4 cxd4 4. Nxd4 Bg7 5. Nc3 Nc6 6. Be3 Nf6 7. Bc4 O-O 8. Bb3 d6 9. f3 Bd7 10. Qd2",
            "sidelines": [],
        },
    ],
    "e4/Sicilian/Dragon/Accelerated Dragon": [
        {
            "label": "Maroczy Approach",
            "line": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. c4 Bg7 6. Be3 Nf6 7. Nc3 O-O 8. Be2 d6 9. O-O Bd7",
            "sidelines": [
                {
                    "label": "7...Ng4 tactical sideline",
                    "line": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. c4 Bg7 6. Be3 Nf6 7. Nc3 Ng4 8. Qxg4 Nxd4 9. Qd1",
                }
            ],
        },
        {
            "label": "Yugoslav Approach",
            "line": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. Nc3 Bg7 6. Be3 Nf6 7. Bc4 O-O 8. Bb3 d6 9. f3 Bd7 10. Qd2",
            "sidelines": [],
        },
    ]
}

HIERARCHY_OPENINGS = {
    "Ruy Lopez": ["ruy-lopez"],
    "Italian": ["italian-game"],
    "Scotch": ["scotch-game"],
    "Petroff": ["petrov-defense"],
    "Vienna": ["vienna-game"],
    "Ponziani": ["ponziani-opening"],
    "King's Gambit": ["kings-gambit"],
    "Philidor": ["philidor-defense"],
    "Sicilian": ["sicilian-defense"],
    "French": ["french-defense"],
    "Caro-Kann": ["caro-kann-defense"],
    "Alekhine": ["alekhine-defense"],
    "Scandinavian": ["scandinavian-defense"],
    "Owen Defense": ["owens-defense"],
    "King's Indian Defense": ["kings-indian-defense"],
    "Nimzo Indian": ["nimzo-indian-defense"],
    "Bogo Indian": ["bogo-indian-defense"],
    "Benoni": ["benoni-defense"],
    "Grunfeld": ["grunfeld-defense"],
    "Trompowsky": ["trompowsky-attack"],
    "Catalan": ["catalan-opening"],
    "Queen's Gambit": ["queens-gambit"],
    "QGA": ["queens-gambit-accepted"],
    "QGD": ["queens-gambit-declined"],
    "Slav": ["slav-defense"],
    "Semi-Slav": ["semi-slav-defense"],
    "Chigorin": ["chigorin-defense"],
    "Albin Counter Gambit": ["albin-countergambit"],
    "Marshall defense": ["marshall-defense"],
    "Baltic defense": ["baltic-defense"],
    "London System": ["london-system"],
    "Colle System": ["colle-system"],
    "Dutch": ["dutch-defense"],
    "Reverse Sicilian": ["english-reversed-sicilian"],
    "Symmetrical English": ["english-symmetrical"],
    "Neo-Catalan": ["english-neo-catalan"],
    "King's Indian Attack": ["kings-indian-attack"],
    "Nimzo-Larsen Attack": ["larsen-opening"],
    "Bird's": ["birds-opening"],
    "Reti (transpositions)": ["reti-opening"],
}

# Defining or decision positions for draft entries that are not yet full guides.
# Keys are complete paths because names such as "Classical" and "Advance" recur.
HIERARCHY_LINES = {
    "e4": "1. e4",
    "e4/e5": "1. e4 e5",
    "e4/e5/4 Knights": "1. e4 e5 2. Nf3 Nc6 3. Nc3 Nf6",
    "e4/e5/Sidelines / Transpositions": "1. e4 e5",
    "e4/e5/Sidelines / Transpositions/Bishops opening": "1. e4 e5 2. Bc4",
    "e4/Sicilian/Najdorf": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6",
    "e4/Sicilian/Classical": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 Nc6",
    "e4/Sicilian/Classical/Direct d6 Move Order": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 Nc6",
    "e4/Sicilian/Classical/Nc6 Transposition": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 d6",
    "e4/Sicilian/Dragon": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6",
    "e4/Sicilian/Dragon/Dragon Sicilian": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6",
    "e4/Sicilian/Dragon/Hyper Accelerated Dragon": "1. e4 c5 2. Nf3 g6",
    "e4/Sicilian/Dragon/Accelerated Dragon": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6",
    "e4/Sicilian/Scheveningen": "1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 d6",
    "e4/Sicilian/Scheveningen/Nf6 before d6": "1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 d6",
    "e4/Sicilian/Scheveningen/Direct d6 Move Order": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e6",
    "e4/Sicilian/4 Knights": "1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3 Nf6",
    "e4/Sicilian/4 Knights/e6 Move Order": "1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3 Nf6",
    "e4/Sicilian/4 Knights/Nc6 Move Order": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e6",
    "e4/Sicilian/Moscow variation": "1. e4 c5 2. Nf3 d6 3. Bb5+",
    "e4/Sicilian/Kan": "1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 a6",
    "e4/Sicilian/Taimanov": "1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6",
    "e4/Sicilian/Rossolimo": "1. e4 c5 2. Nf3 Nc6 3. Bb5",
    "e4/Sicilian/Sveshnikov": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e5",
    "e4/Sicilian/Closed": "1. e4 c5 2. Nc3 Nc6 3. g3",
    "e4/Sicilian/Alapin": "1. e4 c5 2. c3",
    "e4/Sicilian/Alapin/Alapin": "1. e4 c5 2. c3",
    "e4/Sicilian/Alapin/Delayed Alapin Transposition": "1. e4 c5 2. Nf3 d6 3. c3 Nf6",
    "e4/Sicilian/O-Kelly Variation": "1. e4 c5 2. Nf3 a6",
    "e4/Sicilian/Nimsowitsch variation": "1. e4 c5 2. Nf3 Nf6",
    "e4/Sicilian/Katalimov variation": "1. e4 c5 2. Nf3 b6",
    "e4/French/Advance": "1. e4 e6 2. d4 d5 3. e5",
    "e4/French/Tarrasch": "1. e4 e6 2. d4 d5 3. Nd2",
    "e4/French/Classical": "1. e4 e6 2. d4 d5 3. Nc3 Nf6",
    "e4/French/Winawer": "1. e4 e6 2. d4 d5 3. Nc3 Bb4",
    "e4/French/Rubinstein": "1. e4 e6 2. d4 d5 3. Nc3 dxe4",
    "e4/French/Exchange": "1. e4 e6 2. d4 d5 3. exd5 exd5",
    "e4/French/Sidlines": "1. e4 e6",
    "e4/French/Sidlines/2 Knights": "1. e4 e6 2. Nf3 d5 3. Nc3",
    "e4/French/Sidlines/Kings indian attack transposition": "1. e4 e6 2. d3 d5 3. Nd2 Nf6 4. Ngf3",
    "e4/Caro-Kann/Advance": "1. e4 c6 2. d4 d5 3. e5",
    "e4/Caro-Kann/Mainline variation": "1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Bf5",
    "e4/Caro-Kann/Exchange": "1. e4 c6 2. d4 d5 3. exd5 cxd5",
    "e4/Caro-Kann/Sidelines": "1. e4 c6 2. d4 d5",
    "e4/Caro-Kann/Sidelines/Fantasy": "1. e4 c6 2. d4 d5 3. f3",
    "e4/Caro-Kann/Sidelines/Two Knights Attack": "1. e4 c6 2. Nc3 d5 3. Nf3",
    "e4/Caro-Kann/Sidelines/Accelerated Panov Attack": "1. e4 c6 2. d4 d5 3. exd5 cxd5 4. c4",
    "e4/Alternatives": "1. e4",
    "e4/Alternatives/Modern/ Pirc": "1. e4 d6 2. d4 Nf6 3. Nc3 g6",
    "e4/Alternatives/Nimsowitsch Defense": "1. e4 Nc6",
    "d4": "1. d4",
    "d4/Nf6": "1. d4 Nf6",
    "d4/Nf6/Benko": "1. d4 Nf6 2. c4 c5 3. d5 b5",
    "d4/Queen's Gambit/QGD/QGD Exchange Positional Line": "1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. cxd5 exd5",
    "d4/Queen's Gambit/QGD/3 Knights": "1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3",
    "d4/Queen's Gambit/Slav/Slav accepted": "1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 dxc4",
    "d4/Queen's Gambit/Slav/Chebanenko Slav": "1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 a6",
    "d4/Queen's Gambit/Slav/Schlechter variation": "1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 g6",
    "d4/Queen's Gambit/Slav/Quiet Slav": "1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. e3",
    "d4/Queen's Gambit/QG Sidelines": "1. d4 d5 2. c4",
    "d4/Queen's Gambit/QG Sidelines/Austrian defense": "1. d4 d5 2. c4 c5",
    "d4/d4 d5": "1. d4 d5",
    "d4/d4 d5/Jobava London": "1. d4 d5 2. Nc3 Nf6 3. Bf4",
    "d4/Sidelines": "1. d4",
    "d4/Sidelines/Mexican Defense": "1. d4 Nf6 2. c4 Nc6",
    "d4/Sidelines/Mikenas defense": "1. d4 Nc6",
    "d4/Sidelines/Old Benoni": "1. d4 c5",
    "c4 (English)": "1. c4",
    "c4 (English)/Transpositions": "1. c4 Nf6",
    "c4 (English)/Sidelines/ Alternatives": "1. c4",
    "Alternatives/ Sidelines/ Other": "",
}


class GuideDataError(ValueError):
    pass


def _pgn(sans: list[str] | tuple[str, ...]) -> str:
    parts = []
    for index, san in enumerate(sans):
        if index % 2 == 0:
            parts.append(f"{index // 2 + 1}. {san}")
        else:
            parts.append(san)
    return " ".join(parts) if parts else "Starting position"


def _hierarchy_draft(catalogue_by_slug: dict[str, dict], *, load_mainlines: bool = True) -> dict:
    valid_slugs = set(catalogue_by_slug)
    mainline_payload = (
        json.loads(HIERARCHY_MAINLINES_PATH.read_text())
        if load_mainlines and HIERARCHY_MAINLINES_PATH.is_file()
        else {"entries": {}, "method": {}, "source": None}
    )
    mainline_entries = mainline_payload.get("entries", {})
    roots: list[dict] = []
    current_major = current_lesser = current_minor = None
    for raw_line in HIERARCHY_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        marker, _, label = line.partition(" ")
        if marker not in {"&", "%", "=", "\\"} or not label:
            raise GuideDataError(f"invalid hierarchy draft line: {raw_line!r}")
        node = {
            "label": label,
            "level": {"&": "major", "%": "lesser", "=": "minor", "\\": "sub"}[marker],
            "opening_slugs": HIERARCHY_OPENINGS.get(label, []),
            "children": [],
        }
        missing = set(node["opening_slugs"]) - valid_slugs
        if missing:
            raise GuideDataError(f"hierarchy {label}: unknown openings {sorted(missing)}")
        if marker == "&":
            roots.append(node)
            current_major, current_lesser, current_minor = node, None, None
        elif marker == "%":
            if current_major is None:
                raise GuideDataError(f"lesser category without major: {label}")
            current_major["children"].append(node)
            current_lesser, current_minor = node, None
        elif marker == "=":
            if current_lesser is None:
                raise GuideDataError(f"minor category without lesser: {label}")
            current_lesser["children"].append(node)
            current_minor = node
        else:
            if current_minor is None:
                raise GuideDataError(f"subcategory without minor: {label}")
            current_minor["children"].append(node)

    def position_node(position: dict) -> dict:
        return {
            "label": position["label"],
            "level": "position",
            "opening_slugs": [],
            "children": [position_node(child) for child in position.get("children", [])],
            "_line": position["line"],
            "_sidelines": position.get("sidelines", []),
        }

    def inject_position_groups(nodes: list[dict], path: tuple[str, ...]) -> None:
        for node in nodes:
            current_path = (*path, node["label"])
            path_key = "/".join(current_path)
            for position in HIERARCHY_POSITION_GROUPS.get(path_key, []):
                node["children"].append(position_node(position))
            inject_position_groups(node["children"], current_path)

    inject_position_groups(roots, ())

    def enrich(node: dict, path: tuple[str, ...], inherited_line: str) -> None:
        current_path = (*path, node["label"])
        path_key = "/".join(current_path)
        if len(current_path) == 3 and current_path[:2] == ("e4", "Sicilian"):
            node["level"] = "family"
        node["child_role"] = "key_positions" if path_key in KEY_POSITION_FAMILIES else "categories"
        line = node.pop("_line", None) or HIERARCHY_LINES.get(path_key)
        if line is None and node["opening_slugs"]:
            line = " ".join(catalogue_by_slug[node["opening_slugs"][0]]["moves_san"])
        if line is None:
            line = inherited_line
        parsed = _position(line, f"hierarchy {path_key}")
        node["position_data"] = _position_fields(parsed)
        node["pgn"] = _pgn(parsed.san_sequence)
        node["sidelines"] = []
        for sideline_index, sideline in enumerate(node.pop("_sidelines", []), 1):
            sideline_position = _position(
                sideline["line"],
                f"hierarchy {path_key} sideline {sideline_index}",
            )
            node["sidelines"].append({
                "label": sideline["label"],
                "pgn": _pgn(sideline_position.san_sequence),
                "position_data": _position_fields(sideline_position),
            })
        mainline = mainline_entries.get(path_key)
        if mainline:
            if mainline.get("definition_position_key") != parsed.key:
                raise GuideDataError(f"hierarchy {path_key}: mainline definition no longer matches")
            extended = from_uci_sequence(mainline["moves_uci"])
            if list(extended.uci_sequence[:len(parsed.uci_sequence)]) != list(parsed.uci_sequence):
                raise GuideDataError(f"hierarchy {path_key}: mainline does not extend its definition")
            if extended.key != mainline.get("position_key"):
                raise GuideDataError(f"hierarchy {path_key}: stored mainline position is invalid")
            node["mainline_position_data"] = _position_fields(extended)
            node["mainline_pgn"] = _pgn(extended.san_sequence)
            node["mainline_stop_reason"] = mainline.get("stop_reason")
            node["mainline_stop_games"] = mainline.get("continuation_games_at_stop")
            node["mainline_choices"] = mainline.get("choices_at_stop", [])
        else:
            node["mainline_position_data"] = node["position_data"]
            node["mainline_pgn"] = node["pgn"]
            node["mainline_stop_reason"] = "definition_only"
            node["mainline_stop_games"] = None
            node["mainline_choices"] = []
        for child in node["children"]:
            enrich(child, current_path, line)

    for root in roots:
        enrich(root, (), "")
    return {
        "name": "User opening hierarchy draft 2",
        "legend": {"major": "&", "lesser": "%", "minor": "=", "sub": "\\"},
        "mainline_source": mainline_payload.get("source"),
        "mainline_method": mainline_payload.get("method", {}),
        "roots": roots,
    }


def hierarchy_draft_for_generation() -> dict:
    """Build the hierarchy without consulting the generated mainline file."""
    catalogue = _enrich_catalogue(json.loads(CATALOGUE_PATH.read_text()))
    catalogue_by_slug = {entry["slug"]: entry for entry in catalogue["openings"]}
    return _hierarchy_draft(catalogue_by_slug, load_mainlines=False)


def _position(text: str, context: str) -> ParsedPosition:
    try:
        return from_san(text)
    except ValueError as exc:
        raise GuideDataError(f"{context}: {exc}") from exc


def _position_fields(parsed: ParsedPosition) -> dict:
    return {
        "moves_san": list(parsed.san_sequence),
        "moves_uci": list(parsed.uci_sequence),
        "fen": parsed.board.fen(en_passant="legal"),
        "position_key": parsed.key,
        "turn": "white" if parsed.board.turn else "black",
    }


def _enrich_catalogue(payload: dict) -> dict:
    openings = payload.get("openings")
    if not isinstance(openings, list) or not openings:
        raise GuideDataError("opening catalogue has no openings")
    slugs: set[str] = set()
    keys: dict[str, list[str]] = {}
    for entry in openings:
        slug = entry.get("slug")
        if not slug or slug in slugs:
            raise GuideDataError(f"duplicate or missing opening slug: {slug!r}")
        slugs.add(slug)
        parsed = _position(" ".join(entry["moves_san"]), f"catalogue {slug}")
        expected = _position_fields(parsed)
        for field in ("moves_san", "moves_uci", "fen", "position_key"):
            if entry.get(field) != expected[field]:
                raise GuideDataError(f"catalogue {slug}: stored {field} does not match validated line")
        keys.setdefault(parsed.key, []).append(slug)
        for order_index, order in enumerate(entry.get("alternate_move_orders", []), 1):
            alternate = _position(order["san"], f"catalogue {slug} alternate {order_index}")
            if order.get("moves_uci", order.get("uci")) != list(alternate.uci_sequence):
                raise GuideDataError(f"catalogue {slug}: alternate {order_index} has incorrect UCI")
    for entry in openings:
        entry["overlapping_openings"] = [slug for slug in keys[entry["position_key"]] if slug != entry["slug"]]
    return payload


def _enrich_guide(slug: str, guide: dict, catalogue_entry: dict) -> dict:
    defining = _position(guide["defining_line"], f"guide {slug} defining line")
    if defining.key != catalogue_entry["position_key"]:
        raise GuideDataError(f"guide {slug}: defining position does not match catalogue")
    guide["defining_position"] = _position_fields(defining)

    for decision_index, decision in enumerate(guide.get("decisions", []), 1):
        position = _position(decision["position"], f"guide {slug} decision {decision_index}")
        decision["position_data"] = _position_fields(position)
        expected_side = "White" if position.board.turn else "Black"
        if decision.get("side") != expected_side:
            raise GuideDataError(
                f"guide {slug} decision {decision_index}: labelled {decision.get('side')}, but {expected_side} moves"
            )
        seen_moves: set[str] = set()
        for option_index, option in enumerate(decision.get("options", []), 1):
            board = position.board.copy()
            try:
                move = board.parse_san(option["move"])
            except ValueError as exc:
                raise GuideDataError(
                    f"guide {slug} decision {decision_index} option {option_index}: {exc}"
                ) from exc
            uci = move.uci()
            if uci in seen_moves:
                raise GuideDataError(f"guide {slug} decision {decision_index}: duplicate option {uci}")
            seen_moves.add(uci)
            canonical_san = board.san(move)
            board.push(move)
            option["move"] = canonical_san
            option["move_uci"] = uci
            option["line_uci"] = [*position.uci_sequence, uci]
            option["target_fen"] = board.fen(en_passant="legal")
            option["target_position_key"] = " ".join(board.fen(en_passant="legal").split()[:4])

    for line_index, line in enumerate(guide.get("lines", []), 1):
        parsed = _position(line["line"], f"guide {slug} line {line_index} ({line.get('name')})")
        line["position_data"] = _position_fields(parsed)

    for item_index, item in enumerate(guide.get("transpositions", []), 1):
        parsed = _position(item["line"], f"guide {slug} transposition {item_index}")
        item["position_data"] = _position_fields(parsed)
    return guide


def _opening_wiki(hierarchy: dict) -> dict:
    wiki = json.loads(WIKI_PATH.read_text())
    entries = wiki.get("entries", {})
    home = wiki.get("home")
    if not isinstance(home, dict) or not home.get("title") or not home.get("summary"):
        raise GuideDataError("opening wiki has no valid home article")
    valid_paths: set[str] = set()

    def collect(nodes: list[dict], path: tuple[str, ...]) -> None:
        for node in nodes:
            current = (*path, node["label"])
            valid_paths.add("/".join(current))
            collect(node["children"], current)

    collect(hierarchy["roots"], ())
    unknown = set(entries) - valid_paths
    if unknown:
        raise GuideDataError(f"opening wiki has unknown taxonomy paths: {sorted(unknown)}")
    for path, article in {"home": home, **entries}.items():
        if not article.get("title") or not article.get("summary"):
            raise GuideDataError(f"opening wiki article {path!r} is incomplete")
        for source in article.get("sources", []):
            if not source.get("label") or not str(source.get("url", "")).startswith("https://"):
                raise GuideDataError(f"opening wiki article {path!r} has an invalid source")
    return wiki


@lru_cache(maxsize=1)
def opening_data() -> dict:
    catalogue = _enrich_catalogue(json.loads(CATALOGUE_PATH.read_text()))
    guide_payload = json.loads(GUIDES_PATH.read_text())
    raw_guides = guide_payload.get("guides", {})
    catalogue_by_slug = {entry["slug"]: entry for entry in catalogue["openings"]}
    guides: dict[str, dict] = {}
    for slug, guide in raw_guides.items():
        if slug not in catalogue_by_slug:
            raise GuideDataError(f"guide {slug}: not present in catalogue")
        guides[slug] = _enrich_guide(slug, guide, catalogue_by_slug[slug])
    expected = {entry["slug"] for entry in catalogue["openings"] if entry.get("guide_available")}
    if expected != set(guides):
        raise GuideDataError(f"guide availability mismatch: expected {sorted(expected)}, got {sorted(guides)}")
    hierarchy = _hierarchy_draft(catalogue_by_slug)
    wiki = _opening_wiki(hierarchy)
    return {
        "version": max(catalogue.get("version", 1), guide_payload.get("version", 1)),
        "catalogue_source": catalogue["catalogue_source"],
        "independent_reference": catalogue["independent_reference"],
        "sections": catalogue.get("sections", []),
        "selection_criteria": guide_payload["selection_criteria"],
        "openings": catalogue["openings"],
        "hierarchy_draft": hierarchy,
        "wiki": wiki,
        "guides": guides,
    }


def catalogue_response() -> dict:
    payload = opening_data()
    return {
        "version": payload["version"],
        "catalogue_source": payload["catalogue_source"],
        "independent_reference": payload["independent_reference"],
        "selection_criteria": payload["selection_criteria"],
        "sections": payload["sections"],
        "hierarchy_draft": payload["hierarchy_draft"],
        "wiki": payload["wiki"],
        "openings": payload["openings"],
    }


def guide_response(slug: str) -> dict | None:
    return opening_data()["guides"].get(slug)
