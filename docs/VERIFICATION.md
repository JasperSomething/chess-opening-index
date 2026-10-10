# Verification

Run date: 2026-10-06.

## Automated checks

Ten unit tests cover SAN/UCI parsing, FEN parsing, illegal SAN rejection, legal-en-passant canonicalisation, transposition identity, continuation-denominator semantics, preservation of unknown values during source failures, and private token-file permissions.

Five real positions were queried through the new adapters and the old GUI/backend pipeline. Every nonzero move count and every percentage matched exactly for both the cached Lichess population and the installed complete-2200+ population.

| Position | Lichess reach / continuations | Master reach / continuations | Lichess moves | Master moves |
|---|---:|---:|---:|---:|
| Start | 7,826,583,724 / 7,826,583,724 | 2,823,189 / 2,823,189 | 20 | 20 |
| `e4` | 4,573,387,816 / 4,573,387,816 | 1,288,665 / 1,288,665 | 20 | 20 |
| `e4 e5 Nf3` | 1,120,742,504 / 1,120,742,504 | 271,709 / 271,709 | 29 | 13 |
| `d4 Nf6 c4 e6` | 59,158,681 / 59,158,681 | 238,535 / 238,535 | 30 | 16 |
| `c4 e6 d4 Nf6` | 59,158,681 / 59,158,681 | 238,535 / 238,535 | 30 | 16 |

The final two move orders produce the same canonical key and identical results, verifying transposition pooling.

A legal kings-only FEN (`7k/8/8/8/8/8/8/K7 w - - 0 1`) returned known zero reach, zero continuations, and an empty move distribution from the completed installed master index. It is not present in the legacy Lichess cache.

Terminal handling was checked with `6k1/6P1/6K1/8/8/8/8/8 b - - 0 1`: the complete master index reports 217 games reaching the position, zero recorded continuations, and 217 terminal draws. No move frequency is manufactured when the continuation denominator is zero.

## Live API check

The official endpoint `https://explorer.lichess.org/lichess` was contacted successfully using the existing private credential at `~/.config/chess-project/LICHESS_TOKEN`. The application automatically reads that mode-0600 file; the credential was neither displayed nor copied into the project. Official API documentation identifies this endpoint, describes it as aggregated rated games from Lichess players, lists the rating buckets and filters, and declares OAuth2 with no scopes. Live requests are serialized across server threads. HTTP 429 applies a minimum 60-second backoff and honors a longer `Retry-After` value.

The legacy cached positions remain fully usable offline. A token is used automatically only for a cache miss or a changed filter set.

An authenticated uncached check used position `a3 h6` with the single `1800` rating bucket, rapid games, and `since=2025-01`. Before the call, the new cache contained zero rows. The live response added exactly one row and reported 170 position games, 170 continuations, zero terminal records, and 14 moves; frequencies summed to 1.0. Repeating the identical query reported `local_cache`, produced identical moves/counts, and left the cache at one row. No credential content was displayed or persisted.

The automatic GUI path was also checked with a previously uncached `2500`/classical filter. A rapid filter change followed immediately by `e4` ended on the correct current position (Black to move), reported `LIVE · CACHED NOW`, and showed 782 Lichess games. The ignored earlier response did not overwrite the current position. Back and forward then returned `LOCAL CACHE` with 1,629 games at the start and 782 after `e4`, confirming compatible cache reuse without a refresh action.

## GUI and launcher verification

The GUI now uses the previous project's exact `board-fritz.jpg` texture and twelve `piece-alpha-*.svg` assets from `mainlines_ui`. It was rendered with real Chromium at 1440×900, 1024×768, and 700×900 and inspected visually. The board remained square, uncropped, and centred in its column at all three sizes.

Browser geometry was measured on both the 32-piece starting position and the 30-piece line `e4 d5 exd5 Qxd5`. All 64 squares remained identical regardless of occupancy:

| Viewport | Board | Square width range | Square height range | Occupied versus empty |
|---|---:|---:|---:|---|
| 1440×900 | 540×540 | 67.5–67.5 | 67.5–67.5 | identical |
| 1024×768 | 420×420 | 52.5–52.5 | 52.5–52.5 | identical |
| 700×900 | 540×540 | 67.5–67.5 | 67.5–67.5 | identical |

The following interactions were exercised successfully in the rendered page: board move `e4`, table move `e5`, back, forward, history selection, reset, filter changes, an uncached live request, and cached revisits. Turn, board position, line, statistics, and source status followed the current position after every action.

The installed desktop entry under `~/.local/share/applications/` passed `desktop-file-validate`. Launching that installed entry started a healthy local backend and served the board/piece assets; launching it again retained the same server PID rather than starting a duplicate. `Terminal=false` is set, and diagnostics go to `data/run/gui.log`.

## Expected discrepancies

- The Lichess and master counts should differ: they are different populations, dates, rating definitions, and source collections.
- A position may have more Lichess moves because the installed master population is smaller; zero in the completed master index is a real zero, not threshold pruning.
- Cached Lichess counts are snapshots from September 2026 and can differ from a fresh live query as new games are indexed.
- The old threshold-pruned databases can omit rare positions. The selected complete master index does not.
- Terminal games are excluded from frequency denominators. In the ordinary opening samples above there were no terminal records, so reach and continuation totals happen to match.
