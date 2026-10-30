# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=24", "pyyaml>=6"]
# ///
"""Install this repo's spec-kit components into a fresh project and check them.

Usage:
    uv run .github/scripts/check_install.py              # install and check
    uv run .github/scripts/check_install.py min-version  # oldest spec-kit to test

Set SPECIFY to use another specify than the one on PATH, for example
    SPECIFY="uvx --from specify-cli==1.2.3 specify"
"""

import os
import shlex
import sys
from pathlib import Path

from install_check.errors import CheckFailed
from install_check.installation import Installation
from install_check.project import Specify
from install_check.repo import Manifests, SpeckitFloor


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    try:
        if command == "min-version":
            print(SpeckitFloor(Manifests(repo)).tag())
        elif command == "check":
            argv = tuple(shlex.split(os.environ.get("SPECIFY", "specify")))
            print(f"OK: {Installation(repo, Specify(argv)).verify()}")
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except CheckFailed as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
