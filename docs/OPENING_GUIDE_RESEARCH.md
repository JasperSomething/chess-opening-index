# Opening guide research and review

## Catalogue

The starting catalogue retains the 39 entries from the 365Chess opening index and adds six independently validated family positions needed for useful browsing: QGD, QGA, Semi-Slav, English Reversed Sicilian, Symmetrical English, and Neo-Catalan. Names, aliases, source URLs, browsing relationships, defining SAN/UCI sequences, canonical FENs, and position keys are stored in `data/opening_catalogue.json`. The builder cross-checks canonical positions against the Lichess `chess-openings` TSV corpus for ECO codes, independent names, and transpositions. It records rather than hides the erroneous King's Gambit sequence printed by the source index.

One position may retain several names and move orders. Catalogue parents are navigation hints, not a claim that chess openings form a strict tree.

## Pilot selection

The three pilots are Scandinavian Defense, Italian Game, and Queen's Gambit. Candidate choices were kept when they represented at least 1% of continuations in either the default Lichess population or the local both-players-2200+ OTB population at the exact decision position. Lower-frequency moves were retained only for a forcing tactical test, a known theoretical system, or a common trap response. Users can set the display threshold to 0.5%, 1%, 2%, or 5%; this only hides rows and never changes a denominator.

## Catalogue trunk positions

The miniature catalogue boards use `data/opening_hierarchy_mainlines.json`, generated from the complete local both-players-2200+ OTB index. Starting at each validated defining position, the builder follows a continuation only while it has an outright majority and the runner-up remains below 30%. It stops before a plural choice, below 75 recorded continuations, or at the configured depth cap. These are database mainline trunks, not engine recommendations or claims of theoretical best play. The shown next-move shares are conditional at the stop position; they are never multiplied into a purported probability for the complete line.

The lines stop at positions where the plans described in the guide are visible. They were not produced by repeatedly choosing the most frequent move, and position-conditional frequencies are never multiplied together.

## Tactical review

All stored sequences are legal under `python-chess`. Each representative endpoint was spot-checked with the installed Stockfish 19 at depth 12. This check was used to catch concrete tactical misstatements, not to derive strategic prose. In particular, the Albin Countergambit and Marshall Defense examples are explicitly labelled as practically relevant sidelines that favour White in the checked positions.

## Sources

- [365Chess opening index](https://www.365chess.com/chess-openings/) and linked pilot pages: starting names and variations.
- [Lichess chess-openings](https://github.com/lichess-org/chess-openings): independent ECO, PGN/UCI/EPD position data, names, and transpositions.
- [Chess.com Scandinavian](https://www.chess.com/openings/Scandinavian-Defense), [Italian](https://www.chess.com/openings/Italian-Game), and [Queen's Gambit](https://www.chess.com/openings/Queens-Gambit): independent overview references.
- The installed Lumbra positional index and authenticated Lichess Opening Explorer: practical move selection and exact-position frequency display.
