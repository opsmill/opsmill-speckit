"""The releases of this repo."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from packaging.version import InvalidVersion, Version

from install_check.speckit import SpeckitFloor
from repo.components import Components


@dataclass(frozen=True)
class Release:
    """A release of this repo, the oldest Spec Kit it accepts, and its extension.

    The tag is the release number; the extension has its own version.
    """

    tag: str
    version: Version
    min_speckit: Version
    extension: Version


@dataclass(frozen=True)
class ReleaseTags:
    """The vX.Y.Z tags of a repo."""

    root: Path

    def latest(self) -> Release:
        tags = subprocess.run(
            ["git", "-C", str(self.root), "tag", "--list", "v*"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()
        versions = []
        for tag in tags:
            try:
                versions.append((Version(tag.removeprefix("v")), tag))
            except InvalidVersion:
                continue
        if not versions:
            raise SystemExit("no vX.Y.Z tag found; fetch tags first (git fetch --tags)")
        version, tag = max(versions)
        return self.release(tag, version)

    def release(self, tag: str, version: Version) -> Release:
        """The release at a tag, read from the files of that tag."""
        with tempfile.TemporaryDirectory() as tmp:
            archive = subprocess.run(
                ["git", "-C", str(self.root), "archive", tag],
                check=True,
                capture_output=True,
            )
            subprocess.run(["tar", "-x", "-C", tmp], input=archive.stdout, check=True)
            components = Components(Path(tmp))
            return Release(
                tag,
                version,
                SpeckitFloor(components).version(),
                Version(components.extension().version),
            )
