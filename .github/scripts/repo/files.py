"""The files of a repo: YAML files, command front matter and release snapshots."""

import re
import shutil
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
