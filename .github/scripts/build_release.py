# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=24", "pyyaml>=6"]
# ///
"""Build this repo's release zips.

Usage:
    uv run .github/scripts/build_release.py zips DIR         # one zip per component and bundle
"""

import subprocess
import sys
from pathlib import Path

from distribution.archives import build
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


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    command, argument = (sys.argv[1:] + [None, None])[:2]
    if command == "zips" and argument:
        for archive in build(Components(clean(repo)), Path(argument)).values():
            print(f"{archive.path.name}  {archive.sha256()}")
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
