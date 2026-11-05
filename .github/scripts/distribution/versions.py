"""Rules that keep component versions, bundle pins and catalogs in step."""

import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from packaging.version import Version

from distribution.archives import build
from install_check.errors import CheckFailed
from repo.components import Components


def fail_on(errors: list[str]) -> None:
    if errors:
        raise CheckFailed("\n".join(errors))


def zips(repo: Path, dest: Path) -> dict[tuple[str, str], tuple[str, str]]:
    """The version and zip sha256 of each component, by kind and ID."""
    return {
        (component.kind, component.id): (component.version, archive.sha256())
        for component, archive in build(Components(repo), dest).items()
    }


@contextmanager
def worktree(repo: Path, revision: str, dest: Path) -> Iterator[Path]:
    git = ["git", "-C", str(repo), "worktree"]
    subprocess.run([*git, "add", "-q", "--detach", str(dest), revision], check=True)
    try:
        yield dest
    finally:
        subprocess.run([*git, "remove", "--force", str(dest)], check=True)


@dataclass(frozen=True)
class VersionRaised:
    """A component or bundle whose zip changed since a base revision has a higher version.

    spec-kit compares versions, so a change shipped under the same version
    never reaches a project that installed that version. A bundle's zip holds
    its pins, so a new pin changes it.
    """

    repo: Path
    base: str

    def verify(self) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            with worktree(self.repo, self.base, Path(tmp) / "base") as base:
                old = zips(base, Path(tmp) / "old")
            new = zips(self.repo, Path(tmp) / "new")
        changed = [key for key in new if key in old and old[key][1] != new[key][1]]
        fail_on(
            [
                f"{key[1]} changed since {self.base}: raise its version above {old[key][0]}"
                for key in changed
                if Version(new[key][0]) <= Version(old[key][0])
            ]
        )
        return f"{len(changed)} changed components and bundles have a higher version"
