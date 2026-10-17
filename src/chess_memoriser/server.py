from __future__ import annotations

import argparse
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib import parse

from chess_memoriser.adapters.lichess import ALL_RATINGS, ALL_SPEEDS, LichessFilters
from chess_memoriser.config import (
    DEFAULT_CACHE,
    DEFAULT_LEGACY_LICHESS_CACHE,
    DEFAULT_MASTER_DB,
    OLD_PROJECT,
    PROJECT_ROOT,
    load_lichess_token,
)
from chess_memoriser.position import PositionError, from_uci_sequence
from chess_memoriser.engine import StockfishError, analyse, find_stockfish
from chess_memoriser.opening_guides import catalogue_response, guide_response, opening_data
from chess_memoriser.service import position_state, query_sources


STATIC = PROJECT_ROOT / "static"
BOARD_ASSETS = OLD_PROJECT / "mainlines_ui"


def _csv(query: dict[str, list[str]], name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = query.get(name, [","])[0]
    if value == ",":
        return default
    return tuple(part for part in value.split(",") if part)


def serve(
    host: str,
    port: int,
    *,
    cache_path: Path,
    master_db: Path,
    legacy_cache: Path,
    token_file: Path | None,
    stockfish_path: Path | None,
) -> None:
    token = load_lichess_token(token_file)
    stockfish = find_stockfish(stockfish_path)
    opening_data()  # Validate all catalogue and guide lines before accepting requests.
    engine_cache: OrderedDict[tuple[str, int, int], dict] = OrderedDict()
    engine_cache_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def send_content(self, status: int, content: bytes, mime: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", f"{mime}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self) -> None:
            url = parse.urlparse(self.path)
            if url.path == "/api/health":
                self.send_content(
                    200,
                    json.dumps({
                        "app": "chess-memoriser",
                        "status": "ok",
                        "launcher_api": 16,
                        "stockfish_available": stockfish is not None,
                    }).encode(),
                    "application/json",
                )
                return
            if url.path == "/api/openings":
                self.send_content(200, json.dumps(catalogue_response()).encode(), "application/json")
                return
            if url.path.startswith("/api/openings/"):
                slug = parse.unquote(url.path.removeprefix("/api/openings/")).strip("/")
                guide = guide_response(slug)
                if guide is None:
                    self.send_content(404, json.dumps({"error": "Detailed guide is not available yet"}).encode(), "application/json")
                else:
                    self.send_content(200, json.dumps(guide).encode(), "application/json")
                return
            if url.path == "/api/engine":
                try:
                    if stockfish is None:
                        raise StockfishError("No Stockfish executable was found")
                    query = parse.parse_qs(url.query)
                    ucis = tuple(part for part in query.get("moves", [""])[0].split(",") if part)
                    position = from_uci_sequence(ucis)
                    depth = int(query.get("depth", ["16"])[0])
                    multipv = int(query.get("multipv", ["3"])[0])
                    if not 8 <= depth <= 22:
                        raise ValueError("Stockfish depth must be between 8 and 22")
                    if not 1 <= multipv <= 5:
                        raise ValueError("Stockfish MultiPV must be between 1 and 5")
                    key = (position.key, depth, multipv)
                    with engine_cache_lock:
                        result = engine_cache.get(key)
                        if result is not None:
                            engine_cache.move_to_end(key)
                    if result is None:
                        result = analyse(position.board, stockfish, depth=depth, multipv=multipv)
                        with engine_cache_lock:
                            engine_cache[key] = result
                            engine_cache.move_to_end(key)
                            while len(engine_cache) > 256:
                                engine_cache.popitem(last=False)
                    self.send_content(200, json.dumps(result).encode(), "application/json")
                except (PositionError, ValueError) as exc:
                    self.send_content(400, json.dumps({"error": str(exc)}).encode(), "application/json")
                except StockfishError as exc:
                    self.send_content(503, json.dumps({"error": str(exc)}).encode(), "application/json")
                return
            if url.path == "/api/state":
                try:
                    query = parse.parse_qs(url.query)
                    ucis = tuple(part for part in query.get("moves", [""])[0].split(",") if part)
                    # Include every prefix so back/forward navigation through a loaded
                    # guide line is a synchronous client-side operation after one call.
                    prefixes = [
                        position_state(from_uci_sequence(ucis[:cursor]))
                        for cursor in range(len(ucis) + 1)
                    ]
                    self.send_content(
                        200,
                        json.dumps({"current": prefixes[-1], "prefixes": prefixes}).encode(),
                        "application/json",
                    )
                except (PositionError, ValueError) as exc:
                    self.send_content(400, json.dumps({"error": str(exc)}).encode(), "application/json")
                return
            if url.path == "/api/position":
                try:
                    query = parse.parse_qs(url.query)
                    ucis = tuple(part for part in query.get("moves", [""])[0].split(",") if part)
                    ratings = tuple(int(value) for value in _csv(query, "ratings", tuple(map(str, ALL_RATINGS))))
                    speeds = _csv(query, "speeds", ALL_SPEEDS)
                    filters = LichessFilters(
                        ratings,
                        speeds,
                        query.get("since", ["1952-01"])[0],
                        query.get("until", ["3000-12"])[0],
                    )
                    data = query_sources(
                        from_uci_sequence(ucis),
                        cache_path=cache_path,
                        master_db=master_db,
                        legacy_lichess_cache=legacy_cache,
                        filters=filters,
                        token=token,
                        refresh=query.get("refresh", ["0"])[0] == "1",
                    )
                    self.send_content(200, json.dumps(data).encode(), "application/json")
                except (PositionError, ValueError) as exc:
                    self.send_content(400, json.dumps({"error": str(exc)}).encode(), "application/json")
                return

            asset_name = url.path.removeprefix("/ui/") if url.path.startswith("/ui/") else None
            allowed_assets = {"board-fritz.jpg", *(f"piece-alpha-{color}{piece}.svg" for color in "wb" for piece in "KQRBNP")}
            if asset_name in allowed_assets:
                mime = "image/jpeg" if asset_name.endswith(".jpg") else "image/svg+xml"
                self.send_content(200, (BOARD_ASSETS / asset_name).read_bytes(), mime)
                return

            name = {
                "/": "index.html",
                "/app.js": "app.js",
                "/style.css": "style.css",
                "/board-wood4.jpg": "board-wood4.jpg",
            }.get(url.path)
            if not name:
                self.send_error(404)
                return
            mime = {
                "html": "text/html",
                "js": "text/javascript",
                "css": "text/css",
                "jpg": "image/jpeg",
            }[name.rsplit(".", 1)[1]]
            self.send_content(200, (STATIC / name).read_bytes(), mime)

        def log_message(self, _format: str, *_args) -> None:
            return

    print(f"Chess Memoriser: http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serve the Chess Memoriser opening explorer GUI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--master-db", type=Path, default=DEFAULT_MASTER_DB)
    parser.add_argument("--legacy-lichess-cache", type=Path, default=DEFAULT_LEGACY_LICHESS_CACHE)
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--stockfish", type=Path)
    args = parser.parse_args(argv)
    serve(
        args.host,
        args.port,
        cache_path=args.cache,
        master_db=args.master_db,
        legacy_cache=args.legacy_lichess_cache,
        token_file=args.token_file,
        stockfish_path=args.stockfish,
    )


if __name__ == "__main__":
    main()
