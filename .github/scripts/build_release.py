# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=24", "pyyaml>=6"]
# ///
"""Build this repo's release zips and list them in catalog/.

Usage:
    uv run .github/scripts/build_release.py zips DIR              # one zip per component and bundle
    uv run .github/scripts/build_release.py catalog VERSION       # list them in catalog/ for release VERSION
    uv run .github/scripts/build_release.py assets VERSION DIR    # the zips that release VERSION holds

The zips are the same bytes for the same files, so the catalog records the
sha256 of the zips that the release of the same commit publishes.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from distribution.archives import build
from distribution.catalogs import Catalogs, Location
from install_check.errors import CheckFailed
from repo.components import Components


def clean(repo: Path) -> Path:
    """The repo, once checked to have no change and no untracked file.

    Such files would go into the zips, and no commit could rebuild them.
    """
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise SystemExit(f"commit or remove these changes first:\n{status}")
    return repo


def published(repo: Path) -> tuple[str, ...]:
    """Where the GitHub Releases of the repo's tags serve their zips.

    A release that has no tag yet is not published, so its catalog records can
    still change.
    """
    tags = subprocess.run(
        ["git", "-C", str(repo), "tag", "--list", "v*"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    if not tags:
        raise SystemExit("no vX.Y.Z tag found; fetch tags first (git fetch --tags)")
    return tuple(Location.release(tag.removeprefix("v")).archives for tag in tags)


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    command, argument, dest = (sys.argv[1:] + [None, None, None])[:3]
    if command == "zips" and argument:
        for archive in build(Components(clean(repo)), Path(argument)).values():
            print(f"{archive.path.name}  {archive.sha256()}")
    elif command == "catalog" and argument and re.fullmatch(r"\d+\.\d+\.\d+", argument):
        with tempfile.TemporaryDirectory() as tmp:
            archives = build(Components(clean(repo)), Path(tmp))
            Catalogs(repo / "catalog").publish(
                archives, Location.release(argument), published(repo)
            )
        print(f"catalog/ lists the zips of release v{argument}")
    elif (
        command == "assets" and dest and re.fullmatch(r"\d+\.\d+\.\d+", argument or "")
    ):
        archives = build(Components(clean(repo)), Path(dest))
        try:
            assets = Catalogs(repo / "catalog").assets(
                archives, Location.release(argument)
            )
        except CheckFailed as error:
            print(f"FAIL: {error}", file=sys.stderr)
            return 1
        for archive in assets:
            print(archive.path)
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
