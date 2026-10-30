# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=24", "pyyaml>=6"]
# ///
"""Report which repos run an outdated Spec Kit or OpsMill stack.

Usage:
    uv run .github/scripts/audit_repos.py > report.md

Needs ``gh`` with a token that can read every audited repo (GH_TOKEN).
"""

import sys
from datetime import date
from pathlib import Path

from install_check.repo import YamlFile
from repo_audit.github import GraphQL, Organization
from repo_audit.release import ReleaseTags
from repo_audit.report import Report


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    config = YamlFile(root / ".github" / "audit-repos.yml").content()
    repos = sorted(
        (repo for org in config["orgs"] for repo in Organization(org, GraphQL())),
        key=lambda r: r.name,
    )
    release = ReleaseTags(root).latest()
    print(
        Report(repos, release, config.get("in_scope", []), date.today()).text(), end=""
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
