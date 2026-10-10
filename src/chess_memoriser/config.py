import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = PROJECT_ROOT.parents[3]
OLD_PROJECT = WORKSPACE / "2026-09-13/build-a-local-chess-opening-explorer/outputs/chess-explorer"
DEFAULT_MASTER_DB = OLD_PROJECT / "data/lumbra-2200-complete.sqlite"
DEFAULT_LEGACY_LICHESS_CACHE = OLD_PROJECT / "data/lumbra-lichess.sqlite"
DEFAULT_CACHE = PROJECT_ROOT / "data/cache.sqlite"
DEFAULT_TOKEN_FILE = Path.home() / ".config/chess-project/LICHESS_TOKEN"


def load_lichess_token(explicit_file: Path | None = None) -> str | None:
    """Load a token without copying it into project data or configuration."""
    def read_private(path: Path) -> str | None:
        if path.stat().st_mode & 0o077:
            raise PermissionError(f"Refusing Lichess token file with group/other permissions: {path}")
        return path.read_text().strip() or None

    if explicit_file is not None:
        return read_private(explicit_file)
    environment = os.environ.get("LICHESS_TOKEN", "").strip()
    if environment:
        return environment
    if DEFAULT_TOKEN_FILE.is_file():
        return read_private(DEFAULT_TOKEN_FILE)
    return None
