# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=24", "pyyaml>=6"]
# ///
"""Check the versions of this repo's components, bundles and catalogs.

Usage:
    uv run .github/scripts/check_versions.py BASE   # BASE: the revision a pull request is merged into
"""

import sys
from pathlib import Path

from distribution.versions import VersionRaised
from install_check.errors import CheckFailed


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    failed = False
    for check in (VersionRaised(repo, sys.argv[1]),):
        try:
            print(f"ok  {check.verify()}")
        except CheckFailed as error:
            print(f"FAIL: {error}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
