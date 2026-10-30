"""What a repo ships: its manifests and its files."""

import re
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from install_check.errors import CheckFailed


@dataclass(frozen=True)
class YamlFile:
    """A YAML file, read as a mapping that is empty when the file is missing."""

    path: Path

    def content(self) -> dict:
        if not self.path.exists():
            return {}
        return yaml.safe_load(self.path.read_text()) or {}


@dataclass(frozen=True)
class FrontMatter:
    """The YAML front matter of a command file, empty when the file has none."""

    path: Path

    def content(self) -> dict:
        if not self.path.exists():
            return {}
        match = re.match(r"\A---\n(.*?)\n---\n", self.path.read_text(), re.DOTALL)
        return (yaml.safe_load(match.group(1)) or {}) if match else {}


@dataclass(frozen=True)
class Manifests:
    """The manifests of a repo's components."""

    root: Path

    def __iter__(self) -> Iterator[Path]:
        yield self.root / "extension.yml"
        yield from self.presets()
        yield from self.bundles()

    def presets(self) -> list[Path]:
        return sorted(self.root.glob("presets/*/preset.yml"))

    def bundles(self) -> list[Path]:
        return sorted(
            p
            for p in [self.root / "bundle.yml", *self.root.glob("bundles/*/bundle.yml")]
            if p.exists()
        )


@dataclass(frozen=True)
class SpeckitFloor:
    """The oldest spec-kit version that every manifest accepts."""

    manifests: Manifests

    def version(self) -> Version:
        bounds = [bound for path in self.manifests for bound in self.bounds(path)]
        if not bounds:
            raise CheckFailed("no manifest declares requires.speckit_version")
        return max(bounds)

    def bounds(self, path: Path) -> list[Version]:
        spec = (YamlFile(path).content().get("requires") or {}).get("speckit_version")
        if not spec:
            return []
        lower = [Version(s.version) for s in SpecifierSet(spec) if s.operator == ">="]
        if not lower:
            raise CheckFailed(
                f"{path.relative_to(self.manifests.root)}: speckit_version {spec!r} has no inclusive lower bound; use >="
            )
        return lower

    def tag(self) -> str:
        """The version as a spec-kit release tag, X.Y.Z."""
        return ".".join(str(part) for part in (*self.version().release, 0, 0)[:3])


@dataclass(frozen=True)
class Snapshot:
    """The files a release archive of the repo would hold."""

    root: Path

    def copy_to(self, dest: Path) -> Path:
        files = subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split("\0")
        for name in filter(None, files):
            src = self.root / name
            if src.is_file():
                target = dest / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
        return dest
