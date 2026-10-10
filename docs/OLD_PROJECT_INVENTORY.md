# Old project inventory and reuse decision

This inventory describes the private predecessor project inspected during the initial migration. Its machine-specific checkout path is intentionally omitted.

## Data found

| Asset | State and population | Decision |
|---|---|---|
| `data/LumbrasGigaBase_OTB_Complete.pgn` | 8,625,140,207 bytes; 10,355,488 publisher records, release 2026-07-08 | Preserve; no rebuild needed |
| `data/lumbra.sqlite` | Complete all-records import; 138,413 retained positions reachable through >=100-game edges; also carries both-2200 counts at those positions | Do not use as the master authority because rare positions are intentionally absent |
| `data/lumbra-2200.sqlite` | Complete both-2200+ import with its own >=100 retained graph; 46,044 retained positions | Preserve; superseded for direct master queries by the no-cutoff index |
| `data/lumbra-2200-complete.sqlite` | Complete no-cutoff both-2200+ index; 8.65 GB; 2,823,189 accepted games | Reuse read-only as installed master database |
| `data/lumbra-lichess.sqlite` | 27,566 Lichess snapshots and 3,445 legacy online-Masters snapshots; Lichess dates 2026-09-12 to 2026-09-16 | Reuse only compatible Lichess snapshots; do not use online Masters as the installed database |
| `openings.sqlite` | Earlier API cache: 3,445 snapshots per API source, positions through ply 8 | Preserve; its contents are already included in the larger Lichess cache |
| `data/atlas-analysis.sqlite` | Derived curriculum/analysis tables, not an authoritative position index | Not needed for this milestone |

The 8.65 GB index is **not derived from Lichess**. Its input path, byte identity, importer default, pipeline, and stored state all point to the extracted `LumbrasGigaBase_OTB_Complete.pgn`. Source metadata identifies Lumbra’s Gigabase, “OTB Complete”, release 2026-07-08, under CC BY-NC-SA 4.0. It is therefore best labelled **Lumbra OTB collection, both players 2200+**, rather than implying verified titled players or a Lichess 2200 rating bucket.

The full PGN header audit found 3,966,202 White wins, 3,217,700 draws, and 3,171,586 Black wins. It found 1,567,568 records with one or both ratings missing and 2,823,189 records where both ratings are at least 2200. Valid-looking header years span 1749–2026 for 10,353,323 records; 2,165 records are undated or implausibly dated. The publisher does not independently guarantee deduplication, and its nominal OTB collection includes some correspondence, rapid, and blitz-labelled records.

Other local chess folders contain player collections, tournament PGNs, TWIC archives, and engine-game databases, but no other massive positional master index. The Lumbra PGN plus its complete 2200+ positional index is the usable installed master-game source. The old API cache's `masters` rows are the online Lichess Masters population and remain deliberately separate and unused here.

## Formats and counting semantics

The all-games retained graph stores full canonical FEN keys and rows in `counts(position, uci, white, draws, black, white2200, draws2200, black2200)`. Empty UCI is position reach. Its candidate filter cannot lose a qualifying position, but the published graph intentionally retains only the closure of continuations played at least 100 times.

The complete master index stores `edges(position BLOB, move INTEGER, white, draws, black)`. The 34-byte key is lossless, not a hash. Move zero represents a game ending at that position. Summing all edges gives position reach; summing nonzero edges gives the continuation denominator. Each source game contributes once to a position and only its first outgoing move there, so repetitions do not inflate counts.

Accepted master records require a standard start, standard chess, a known result, parseable moves, and numeric ratings of at least 2200 for both players. Source records are not independently deduplicated.

The legacy API cache stores `snapshots` with position W/D/L and raw response JSON plus `moves` with UCI, SAN, target, and move W/D/L. Its Lichess configuration is standard rated chess, every speed and rating bucket, `1952-01` through `3000-12`, with 256 moves requested.

The Lichess enrichment itself is incomplete in breadth: 27,566 cached positions are only a subset of the 138,413 retained local positions. For a cached position, the 256-move response is treated as a complete legal-continuation list; an absent snapshot means “not cached”, never zero Lichess games. A live authenticated query is used for such misses.

## GUI statistics recovered

The old GUI displayed flattened move counts and percentages, while richer counts existed below the presentation layer:

- position reach was stored in snapshot W/D/L or the empty-UCI/aggregate edge rows;
- recorded-continuation totals were derived by summing move rows;
- terminal records were recoverable as position reach minus continuation total, and explicitly as move zero in the complete master index;
- per-move White wins, draws, and Black wins were stored by both the local indexes and Lichess cache but collapsed to one game count in the GUI;
- move frequency was derived from the source's complete continuation total, excluding games ending at the position;
- transpositions were pooled through canonical position identity, rather than counted as separate lines;
- the old GUI's `parents` count described incoming frequent master-API edges and is navigation metadata, not a move-distribution statistic, so it is not part of the new source contract.

The old online `masters` snapshots are deliberately not substituted for the installed master database.
