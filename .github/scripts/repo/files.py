"""The files of a repo: YAML files, command front matter and release snapshots."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml


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
class Snapshot:
    """The files a release archive of the repo would hold."""

    root: Path

    def files(self) -> list[str]:
        """Tracked and unignored files, as paths from the root."""
        return self._ls("--cached", "--others", "--exclude-standard")

    def ignored(self, rules: str) -> list[str]:
        """The files that the rules file ignores, as paths from the root.

        Only those rules count: the git configuration of the machine, such as
        its global excludes, must not change what a release archive holds.
        """
        return self._ls("--cached", "--others", "--ignored", f"--exclude-from={rules}")

    def _ls(self, *options: str) -> list[str]:
        names = subprocess.run(
            ["git", "-C", str(self.root), "ls-files", "-z", *options],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split("\0")
        return sorted(name for name in names if name and (self.root / name).is_file())
