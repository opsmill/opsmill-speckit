import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from install_check.project import Project


@dataclass(frozen=True)
class FakeSpecify:
    """A specify that does nothing."""

    def run(self, cwd: Path, *args: str, confirm: bool = False) -> str:
        return ""


@pytest.fixture
def project(tmp_path: Path) -> Project:
    """An initialized spec-kit project."""
    path = tmp_path / "project"
    (path / ".specify").mkdir(parents=True)
    (path / ".specify" / "integration.json").write_text(
        json.dumps({"integration": "claude"})
    )
    return Project(path, FakeSpecify())
