# Chess Memoriser — opening explorer and guide

This milestone accepts a legal SAN sequence or FEN and returns two explicitly separate move distributions:

1. aggregated rated **Lichess player games**, using the official Opening Explorer and compatible cached responses;
2. the already-installed **Lumbra master database**, restricted to games where both players are rated 2200+.

The application now combines the database explorer, compact Stockfish analysis, and a searchable, grouped opening catalogue. Strategic pilot guides are available for the Scandinavian Defense, Italian Game, and the Queen's Gambit family overview; the command-line data API remains available for scripts. It deliberately has no repertoire builder, drill system, or account layer.

## Setup

Clone the repository and create a virtual environment:

```bash
git clone git@github.com:JasperSomething/chess-opening-index.git
cd chess-opening-index
python3 -m venv .venv
.venv/bin/pip install -e .
```

The final command installs the application and its Python dependencies into the isolated environment.

## Run

Cached default-population query (works without network or a token when that position is in the reused cache):

```bash
.venv/bin/chess-memoriser --moves "e4 e5 Nf3" --offline --pretty
```

FEN query:

```bash
.venv/bin/chess-memoriser \
  --fen "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2" \
  --pretty
```

Live Lichess query with explicit filters:

```bash
export LICHESS_TOKEN="your_personal_token"
.venv/bin/chess-memoriser \
  --moves "e4 c5 Nf3" \
  --ratings 2200,2500 \
  --speeds blitz,rapid,classical \
  --since 2020-01 \
  --until 3000-12 \
  --pretty
```

You can instead use `--token-file /private/path/LICHESS_TOKEN`. Tokens are never written to the cache or output. The official Explorer now requires OAuth2 authentication; an empty-scope personal token is sufficient. The program sends one request at a time, spaces live calls by three seconds, and on HTTP 429 waits at least 60 seconds while honoring a longer `Retry-After` value.

If neither `--token-file` nor `LICHESS_TOKEN` is supplied, the application securely reads the mode-600 credential at `~/.config/chess-project/LICHESS_TOKEN`. Only the path is configured; the secret is never copied into this project, its SQLite cache, logs, or API responses.

References: [official Lichess Explorer operation](https://github.com/lichess-org/api/blob/master/doc/specs/tags/openingexplorer/lichess.yaml) and [official API rate-limit guidance](https://lichess.org/page/api-tips).

Default filters are explicit: standard chess; rated games; all nine Lichess rating buckets; all six speeds; `1952-01` through `3000-12`. A different filter set gets a separate cache key and never reuses incompatible old data.

## Output meaning

Each source reports:

- `position_games`: games that reached the position, including games ending there;
- `continuation_games`: games having a recorded next move;
- `terminal_games`: `position_games - continuation_games`;
- position-level and move-level White-win/draw/Black-win counts;
- `frequency`: move games divided by **all recorded continuations for that source**.

The `moves=256` Explorer request is larger than the maximum legal move count, so returned frequencies are not renormalised over a short display list. Missing values are `null`; known absence in the completed installed master index is zero.

## Reused assets

- `data/lumbra-2200-complete.sqlite` is read in place through its lossless 34-byte position key. It is complete, not sampled, has no frequency threshold, and contains 2,823,189 accepted both-2200+ games.
- `data/lumbra-lichess.sqlite` supplies compatible cached Lichess snapshots for 27,566 positions under the default filters. Live responses go only to this new project's `data/cache.sqlite`.
- The canonical legal-en-passant FEN identity, compact-key encoding, W/D/L semantics, serial retry behavior, and cache validation were adapted from the old code.

No old database or source file is modified. See [the old-project inventory](docs/OLD_PROJECT_INVENTORY.md) and [verification results](docs/VERIFICATION.md).

The legacy Lichess cache is partial coverage: a cache miss is unknown, not zero. If a live call cannot be made, that source is returned with `available: false` and `null` totals while the installed master result remains usable.

## Local GUI

```bash
.venv/bin/chess-memoriser-gui --port 8879
```

Open <http://127.0.0.1:8879>. The board accepts legal moves by square click; database, guide, and Stockfish rows also play moves. Back, forward, reset, move-line navigation, and rating/speed changes automatically load compatible cached statistics or fetch them live. Loading, cache origin, and source errors are visible in the interface.

The **Openings** view searches 39 validated families by name, alias, or ECO and loads each defining position. Its three pilot guides present position-linked decisions for both sides, representative lines, practical sidelines, transpositions, and plans. The **Database Explorer** view remains unrestricted. Display thresholds are configurable and never change the source denominator.

Catalogue names and starting sequences were transcribed from [365Chess](https://www.365chess.com/chess-openings/) and checked against the independent [Lichess opening-name dataset](https://github.com/lichess-org/chess-openings). Every stored sequence is parsed by `python-chess` at application startup. The catalogue corrects the source index's King's Gambit typo to `1. e4 e5 2. f4`; the original URL and a correction note remain in its metadata. Explanations are original and the guide source links include the relevant 365Chess and Chess.com opening references.

Pilot alternatives were selected when they reached at least 1% in either the active Lichess population or the local both-2200+ OTB index, with lower-frequency forcing or theoretically important exceptions retained. The interface exposes 0.5%, 1%, 2%, and 5% display thresholds. Frequencies are conditional on the exact current position; line frequencies are never multiplied into a purported complete-line probability.

The compact Stockfish panel reuses the installed Stockfish 19 binary retained by the old project. It analyses each current position automatically, defaults to three lines at depth 16, and reports scores explicitly from the side-to-move perspective. Position keys are checked before results are rendered, so an earlier analysis cannot appear beneath a later board. Depth, line-count, and pause controls remain available. `--stockfish PATH` or `STOCKFISH_EXECUTABLE` can override the detected executable.

Guide lines preload their complete sequence of board states. Back, forward, and move-history navigation therefore update the board immediately; database statistics and engine analysis load independently after the board has moved. Strategic guides lead with **Reach a useful position**, use a compact choice map, and collapse locally rare practical alternatives instead of giving them main-system prominence.

On this machine, launch **Chess Memoriser** from the desktop application menu. It starts the local service only when needed, reuses an existing healthy instance, opens the interface automatically, and writes diagnostics to `data/run/gui.log` without opening a terminal.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```
