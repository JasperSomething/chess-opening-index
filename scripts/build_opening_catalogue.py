from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from chess_memoriser.position import PositionError, from_san


SOURCE_ROOT = "https://www.365chess.com"
LICHESS_REFERENCE = "https://github.com/lichess-org/chess-openings"

# Starting catalogue transcribed from the 365Chess mega index. The King's Gambit
# move sequence is deliberately corrected below rather than preserving its typo.
RAW = [
    ("ruy-lopez", "Ruy Lopez", ["Spanish Opening"], "1. e4 e5 2. Nf3 Nc6 3. Bb5", "Open Games", ["King's Pawn Game"], "/chess-openings/Ruy-Lopez", "C60-C99"),
    ("italian-game", "Italian Game", ["Italian Opening"], "1. e4 e5 2. Nf3 Nc6 3. Bc4", "Open Games", ["King's Pawn Game"], "/chess-openings/Italian-Game", "C50-C59"),
    ("scotch-game", "Scotch Game", ["Scotch Opening"], "1. e4 e5 2. Nf3 Nc6 3. d4", "Open Games", ["King's Pawn Game"], "/chess-openings/Scotch-Game", "C44-C45"),
    ("sicilian-defense", "Sicilian Defense", ["Sicilian Defence"], "1. e4 c5", "Semi-Open Games", ["King's Pawn Game"], "/chess-openings/Sicilian-Defense", "B20-B99"),
    ("french-defense", "French Defense", ["French Defence"], "1. e4 e6 2. d4 d5", "Semi-Open Games", ["King's Pawn Game"], "/chess-openings/French-Defense", "C00-C19"),
    ("scandinavian-defense", "Scandinavian Defense", ["Scandinavian Defence", "Center Counter Defense", "Center Counter Game"], "1. e4 d5", "Semi-Open Games", ["King's Pawn Game"], "/chess-openings/Scandinavian-Defense", "B01"),
    ("petrov-defense", "Petrov's Defense", ["Petroff Defense", "Russian Game"], "1. e4 e5 2. Nf3 Nf6", "Open Games", ["King's Pawn Game"], "/chess-openings/Petrovs-Defense", "C42-C43"),
    ("philidor-defense", "Philidor Defense", ["Philidor's Defence"], "1. e4 e5 2. Nf3 d6", "Open Games", ["King's Pawn Game"], "/chess-openings/Philidor-Defense", "C41"),
    ("kings-gambit", "King's Gambit", [], "1. e4 e5 2. f4", "Open Games", ["King's Pawn Game"], "/chess-openings/Kings-Gambit", "C30-C39"),
    ("caro-kann-defense", "Caro-Kann Defense", ["Caro-Kann Defence"], "1. e4 c6", "Semi-Open Games", ["King's Pawn Game"], "/chess-openings/Caro-Kann-Defense", "B10-B19"),
    ("modern-defense", "Modern Defense", ["Robatsch Defense"], "1. e4 g6", "Semi-Open Games", ["King's Pawn Game"], "/chess-openings/Modern-Defense", "B06"),
    ("pirc-defense", "Pirc Defense", ["Pirc Defence"], "1. e4 d6", "Semi-Open Games", ["King's Pawn Game"], "/chess-openings/Pirc-Defense", "B07-B09"),
    ("owens-defense", "Owen's Defense", ["Queen's Fianchetto Defense"], "1. e4 b6", "Semi-Open Games", ["King's Pawn Game"], "/chess-openings/Owens-Defense", "B00"),
    ("alekhine-defense", "Alekhine Defense", ["Alekhine's Defence"], "1. e4 Nf6", "Semi-Open Games", ["King's Pawn Game"], "/chess-openings/Alekhines-Defense", "B02-B05"),
    ("vienna-game", "Vienna Game", ["Vienna Opening"], "1. e4 e5 2. Nc3", "Open Games", ["King's Pawn Game"], "/chess-openings/Vienna-Game", "C25-C29"),
    ("ponziani-opening", "Ponziani Opening", ["Ponziani Game"], "1. e4 e5 2. Nf3 Nc6 3. c3", "Open Games", ["King's Pawn Game"], "/chess-openings/Ponziani-Opening", "C44"),
    ("kings-indian-defense", "King's Indian Defense", ["King's Indian Defence"], "1. d4 Nf6 2. c4 g6", "Indian Defenses", ["Queen's Pawn Game"], "/chess-openings/Kings-Indian-Defense", "E60-E99"),
    ("grunfeld-defense", "Grünfeld Defense", ["Grunfeld Defense", "Grünfeld Defence"], "1. d4 Nf6 2. c4 g6 3. Nc3 d5", "Indian Defenses", ["Queen's Pawn Game"], "/chess-openings/Grunfeld-Defense", "D70-D99"),
    ("benoni-defense", "Benoni Defense", ["Benoni Defence"], "1. d4 Nf6 2. c4 c5", "Indian Defenses", ["Queen's Pawn Game"], "/chess-openings/Benoni-Defense", "A56-A79"),
    ("budapest-gambit", "Budapest Gambit", ["Budapest Defense"], "1. d4 Nf6 2. c4 e5", "Indian Defenses", ["Queen's Pawn Game"], "/chess-openings/Budapest-Gambit", "A51-A52"),
    ("queens-indian-defense", "Queen's Indian Defense", ["Queen's Indian Defence"], "1. d4 Nf6 2. c4 e6 3. Nf3 b6", "Indian Defenses", ["Queen's Pawn Game"], "/chess-openings/Queens-Indian-Defense", "E12-E19"),
    ("queens-gambit", "Queen's Gambit", ["Aleppo Gambit"], "1. d4 d5 2. c4", "Closed Games", ["Queen's Pawn Game"], "/chess-openings/Queens-Gambit", "D06-D69"),
    ("queens-gambit-declined", "Queen's Gambit Declined", ["QGD"], "1. d4 d5 2. c4 e6", "Closed Games", ["Queen's Gambit"], "/chess-openings/Queens-Gambit-Declined", "D30-D69"),
    ("queens-gambit-accepted", "Queen's Gambit Accepted", ["QGA"], "1. d4 d5 2. c4 dxc4", "Closed Games", ["Queen's Gambit"], "/chess-openings/Queens-Gambit-Accepted", "D20-D29"),
    ("slav-defense", "Slav Defense", ["Slav Defence"], "1. d4 d5 2. c4 c6", "Closed Games", ["Queen's Gambit"], "/chess-openings/Slav-Defense", "D10-D19"),
    ("semi-slav-defense", "Semi-Slav Defense", ["Semi-Slav Defence"], "1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 e6", "Closed Games", ["Queen's Gambit", "Slav Defense"], "/chess-openings/Semi-Slav-Defense", "D43-D49"),
    ("colle-system", "Colle System", ["Colle Opening"], "1. d4 d5 2. Nf3 Nf6 3. e3", "Closed Games", ["Queen's Pawn Game"], "/chess-openings/Colle-System", "D04-D05"),
    ("london-system", "London System", [], "1. d4 d5 2. Bf4", "Closed Games", ["Queen's Pawn Game"], "/chess-openings/London-System", "D00-D02"),
    ("chigorin-defense", "Chigorin Defense", ["Chigorin Defence"], "1. d4 d5 2. c4 Nc6", "Closed Games", ["Queen's Gambit"], "/chess-openings/Chigorin-Defense", "D07"),
    ("marshall-defense", "Marshall Defense", ["Marshall Defence"], "1. d4 d5 2. c4 Nf6", "Closed Games", ["Queen's Gambit"], "/chess-openings/Marshall-Defense", "D06"),
    ("albin-countergambit", "Albin Countergambit", ["Albin Counter-Gambit"], "1. d4 d5 2. c4 e5", "Closed Games", ["Queen's Gambit"], "/chess-openings/Albin-Counter-Gambit", "D08-D09"),
    ("baltic-defense", "Baltic Defense", ["Grau Defense", "Sahović Defense"], "1. d4 d5 2. c4 Bf5", "Closed Games", ["Queen's Gambit"], "/chess-openings/Baltic-Defense", "D06"),
    ("nimzo-indian-defense", "Nimzo-Indian Defense", ["Nimzo-Indian Defence"], "1. d4 Nf6 2. c4 e6 3. Nc3 Bb4", "Indian Defenses", ["Queen's Pawn Game"], "/chess-openings/Nimzo-Indian-Defense", "E20-E59"),
    ("bogo-indian-defense", "Bogo-Indian Defense", ["Bogo-Indian Defence"], "1. d4 Nf6 2. c4 e6 3. Nf3 Bb4+", "Indian Defenses", ["Queen's Pawn Game"], "/chess-openings/Bogo-Indian-Defense", "E11"),
    ("trompowsky-attack", "Trompowsky Attack", ["Trompowsky Opening"], "1. d4 Nf6 2. Bg5", "Indian Defenses", ["Queen's Pawn Game"], "/chess-openings/Trompowsky-Attack", "A45"),
    ("dutch-defense", "Dutch Defense", ["Dutch Defence"], "1. d4 f5", "Flank and Other Openings", ["Queen's Pawn Game"], "/chess-openings/Dutch-Defense", "A80-A99"),
    ("catalan-opening", "Catalan Opening", ["Catalan"], "1. d4 Nf6 2. c4 e6 3. g3", "Indian Defenses", ["Queen's Pawn Game"], "/chess-openings/Catalan-Opening", "E00-E09"),
    ("english-opening", "English Opening", [], "1. c4", "Flank and Other Openings", ["Flank Opening"], "/chess-openings/English-Opening", "A10-A39"),
    ("english-reversed-sicilian", "English: Reversed Sicilian", ["King's English"], "1. c4 e5", "Flank and Other Openings", ["English Opening"], "/eco/A20-A29_English_opening", "A20-A29"),
    ("english-symmetrical", "English: Symmetrical", ["Symmetrical English"], "1. c4 c5", "Flank and Other Openings", ["English Opening"], "/eco/A30-A39_English_symmetrical", "A30-A39"),
    ("english-neo-catalan", "English: Neo-Catalan", ["Neo-Catalan Opening"], "1. c4 Nf6 2. Nf3 e6 3. g3 d5 4. Bg2 Be7 5. O-O O-O", "Flank and Other Openings", ["English Opening"], "/eco/A13-A14_English_Neo-Catalan", "A13-A14"),
    ("reti-opening", "Réti Opening", ["Reti Opening"], "1. Nf3", "Flank and Other Openings", ["Flank Opening"], "/chess-openings/Reti-Opening", "A04-A09"),
    ("kings-indian-attack", "King's Indian Attack", ["KIA"], "1. Nf3 d5 2. d3", "Flank and Other Openings", ["Réti Opening"], "/eco/A06_Reti_old_Indian_attack", "A05-A08"),
    ("larsen-opening", "Larsen's Opening", ["Nimzo-Larsen Attack", "Nimzowitsch-Larsen Attack"], "1. b3", "Flank and Other Openings", ["Flank Opening"], "/eco/A01_Nimzovich-Larsen_attack", "A01"),
    ("birds-opening", "Bird's Opening", ["Bird Opening"], "1. f4", "Flank and Other Openings", ["Flank Opening"], "/chess-openings/Birds-Opening", "A02-A03"),
]


# This is a browsing taxonomy, not an attempt to force transposing positions into
# a strict tree. Umbrellas retain their metadata and guides, while the catalogue
# presents the distinct families a player actually chooses between.
CATALOGUE_STRUCTURE = [
    ("1.e4", "1.e4 openings", [
        ("e4-e5", "1...e5 · Open games", "Black meets the centre directly; choose the distinct White system or Black defence below.", [
            "ruy-lopez", "italian-game", "scotch-game", "vienna-game", "petrov-defense",
            "kings-gambit", "ponziani-opening",
        ]),
        ("sicilian", "1...c5 · Sicilian", "The major asymmetric reply to 1.e4.", ["sicilian-defense"]),
        ("french", "1...e6 · French", "Black prepares ...d5 and accepts a temporarily restricted light bishop.", ["french-defense"]),
        ("caro-kann", "1...c6 · Caro-Kann", "Black prepares ...d5 while keeping the light bishop available.", ["caro-kann-defense"]),
        ("other-e4", "Other replies to 1.e4", "Important alternatives, grouped below the four major reply families.", [
            "scandinavian-defense", "alekhine-defense", "pirc-defense", "modern-defense", "philidor-defense", "owens-defense",
        ]),
    ]),
    ("queens-gambit-complex", "Queen's Gambit complex", [
        ("slav-family", "Slav families", "Black supports d5 with ...c6 and keeps the c8-bishop outside the pawn chain.", [
            "slav-defense", "semi-slav-defense",
        ]),
        ("qgd-family", "Queen's Gambit Declined", "Black maintains the d5 strongpoint with ...e6.", ["queens-gambit-declined"]),
        ("qga-and-sidelines", "Queen's Gambit Accepted + other replies", "The accepted game and the less common independent replies to 2.c4.", [
            "queens-gambit-accepted", "chigorin-defense", "marshall-defense", "albin-countergambit", "baltic-defense",
        ]),
    ]),
    ("other-d4", "Other 1.d4 openings", [
        ("indian-defenses", "Indian defenses", "Systems beginning with 1...Nf6, including their major transpositional families.", [
            "kings-indian-defense", "grunfeld-defense", "nimzo-indian-defense", "queens-indian-defense",
            "bogo-indian-defense", "benoni-defense", "budapest-gambit", "catalan-opening", "trompowsky-attack",
        ]),
        ("d4-systems", "Queen's-pawn systems", "White systems that do not begin with an immediate 2.c4 Queen's Gambit.", ["london-system", "colle-system"]),
    ]),
    ("english", "English Opening · 1.c4", [
        ("english-main", "English families", "Distinct structures after 1.c4; transpositions remain linked rather than collapsed.", [
            "english-reversed-sicilian", "english-symmetrical", "english-neo-catalan",
        ]),
    ]),
    ("bird-dutch", "Bird & Dutch", [
        ("bird-dutch", "Related f-pawn openings", "Bird's Opening and the Dutch are colour-reversed relatives, but remain distinct openings.", ["birds-opening", "dutch-defense"]),
    ]),
    ("other-flank", "Other flank openings", [
        ("other-flank", "Réti and other flank systems", "Flexible openings whose final family is often determined by transposition.", [
            "reti-opening", "kings-indian-attack", "larsen-opening",
        ]),
    ]),
]

UMBRELLA_OPENINGS = {"queens-gambit", "english-opening"}

ALTERNATE_ORDERS = {
    "italian-game": ["1. e4 e5 2. Bc4 Nc6 3. Nf3"],
    "french-defense": ["1. e4 e6 2. d4 d5", "1. d4 e6 2. e4 d5"],
    "queens-gambit": ["1. d4 d5 2. c4"],
    "colle-system": ["1. d4 d5 2. e3 Nf6 3. Nf3"],
    "catalan-opening": ["1. d4 Nf6 2. c4 e6 3. g3", "1. Nf3 Nf6 2. g3 e6 3. Bg2 d5 4. d4 Be7 5. O-O O-O 6. c4"],
    "kings-indian-attack": ["1. e4 e6 2. d3 d5 3. Nd2 Nf6 4. Ngf3"],
}


def lichess_positions(directory: Path) -> dict[str, list[dict]]:
    positions: dict[str, list[dict]] = {}
    for volume in "abcde":
        with (directory / f"{volume}.tsv").open(newline="") as source:
            for row in csv.DictReader(source, delimiter="\t"):
                try:
                    parsed = from_san(row["pgn"])
                except PositionError:
                    continue
                positions.setdefault(parsed.key, []).append({
                    "name": row["name"],
                    "eco": row["eco"],
                    "moves": " ".join(parsed.san_sequence),
                })
    return positions


def build(directory: Path) -> dict:
    reference = lichess_positions(directory)
    taxonomy = {}
    sections = []
    for section_order, (section_id, section_label, families) in enumerate(CATALOGUE_STRUCTURE):
        section = {
            "id": section_id,
            "label": section_label,
            "order": section_order,
            "overview_slug": "queens-gambit" if section_id == "queens-gambit-complex" else None,
            "families": [],
        }
        for family_order, (family_id, family_label, description, members) in enumerate(families):
            section["families"].append({
                "id": family_id,
                "label": family_label,
                "description": description,
                "order": family_order,
                "members": members,
            })
            for opening_order, slug in enumerate(members):
                if slug in taxonomy:
                    raise ValueError(f"opening appears twice in catalogue structure: {slug}")
                taxonomy[slug] = {
                    "section": section_id,
                    "section_label": section_label,
                    "section_order": section_order,
                    "family": family_id,
                    "family_label": family_label,
                    "family_order": family_order,
                    "opening_order": opening_order,
                }
        sections.append(section)
    openings = []
    for slug, name, aliases, moves, group, parents, path, eco_fallback in RAW:
        parsed = from_san(moves)
        alternatives = []
        for alternate in ALTERNATE_ORDERS.get(slug, []):
            other = from_san(alternate)
            alternatives.append({
                "san": " ".join(other.san_sequence),
                "uci": list(other.uci_sequence),
                "position_key": other.key,
                "same_defining_position": other.key == parsed.key,
            })
        matches = reference.get(parsed.key, [])
        ecos = sorted({match["eco"] for match in matches}) or [eco_fallback]
        position_names = sorted({match["name"] for match in matches})
        browse = taxonomy.get(slug)
        if not browse and slug not in UMBRELLA_OPENINGS:
            raise ValueError(f"opening missing from catalogue structure: {slug}")
        openings.append({
            "slug": slug,
            "name": name,
            "aliases": aliases,
            "group": group,
            "parents": parents,
            "eco": ecos,
            "eco_family": eco_fallback,
            "moves_san": list(parsed.san_sequence),
            "moves_uci": list(parsed.uci_sequence),
            "fen": parsed.board.fen(en_passant="legal"),
            "position_key": parsed.key,
            "alternate_move_orders": alternatives,
            "position_names": position_names,
            "source_url": SOURCE_ROOT + path,
            "independent_reference_url": LICHESS_REFERENCE,
            "source_correction": (
                "365Chess currently prints 1.e4 d5 for this entry; corrected to 1.e4 e5 2.f4 and independently validated."
                if slug == "kings-gambit" else None
            ),
            "guide_available": slug in {"scandinavian-defense", "italian-game", "queens-gambit"},
            "catalogue_role": "umbrella" if slug in UMBRELLA_OPENINGS else "opening",
            **(browse or {}),
        })
    return {
        "version": 2,
        "catalogue_source": "https://www.365chess.com/chess-openings/",
        "independent_reference": LICHESS_REFERENCE,
        "sections": sections,
        "openings": openings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lichess-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.lichess_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(payload['openings'])} validated openings to {args.output}")


if __name__ == "__main__":
    main()
