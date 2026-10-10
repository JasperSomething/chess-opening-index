from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from chess_memoriser.adapters.lichess import ALL_RATINGS, ALL_SPEEDS, LichessFilters
from chess_memoriser.config import DEFAULT_CACHE, DEFAULT_LEGACY_LICHESS_CACHE, DEFAULT_MASTER_DB, load_lichess_token
from chess_memoriser.position import PositionError, parse_position
from chess_memoriser.service import query_sources


def comma_ints(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(item) for item in value.split(",") if item)
    except ValueError:
        raise argparse.ArgumentTypeError("ratings must be comma-separated integers") from None


def comma_strings(value: str) -> tuple[str, ...]:
    return tuple(item for item in value.split(",") if item)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess-memoriser",
        description="Return separate Lichess-player and installed-master move distributions.",
    )
    position = parser.add_mutually_exclusive_group(required=True)
    position.add_argument("--moves", help='Legal SAN sequence, for example: "e4 e5 Nf3"')
    position.add_argument("--fen", help="A legal standard-chess FEN")
    parser.add_argument("--ratings", type=comma_ints, default=ALL_RATINGS, help="Lichess rating buckets")
    parser.add_argument("--speeds", type=comma_strings, default=ALL_SPEEDS, help="Lichess speed names")
    parser.add_argument("--since", default="1952-01", help="Lichess lower month bound, YYYY-MM")
    parser.add_argument("--until", default="3000-12", help="Lichess upper month bound, YYYY-MM")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--master-db", type=Path, default=DEFAULT_MASTER_DB)
    parser.add_argument("--legacy-lichess-cache", type=Path, default=DEFAULT_LEGACY_LICHESS_CACHE)
    parser.add_argument("--token-file", type=Path, help="Optional Lichess bearer token; not required by Explorer")
    parser.add_argument("--offline", action="store_true", help="Use matching local/legacy cache only")
    parser.add_argument("--refresh", action="store_true", help="Bypass caches and fetch Lichess now")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.offline and args.refresh:
        parser.error("--offline and --refresh cannot be used together")
    try:
        parsed = parse_position(moves=args.moves, fen=args.fen)
        filters = LichessFilters(args.ratings, args.speeds, args.since, args.until)
        token = load_lichess_token(args.token_file)
        data = query_sources(
            parsed,
            cache_path=args.cache,
            master_db=args.master_db,
            legacy_lichess_cache=args.legacy_lichess_cache,
            filters=filters,
            token=token,
            offline=args.offline,
            refresh=args.refresh,
        )
    except (OSError, ValueError, RuntimeError, PositionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(data, indent=2 if args.pretty else None, sort_keys=args.pretty))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
