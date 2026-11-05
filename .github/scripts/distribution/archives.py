"""The release zips of a repo's components."""

import hashlib
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from repo.components import Component

# Members are stored without compression and with a fixed date, so that the
# same files give the same bytes on any machine and with any zlib.
TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def build(components: Iterable[Component], dest: Path) -> dict[Component, "Archive"]:
    """The zip of each component, written in dest."""
    return {component: Archive.of(component, dest) for component in components}


@dataclass(frozen=True)
class Archive:
    """A release zip."""

    path: Path

    @classmethod
    def of(cls, component: Component, dest: Path) -> "Archive":
        """The zip of a component, named <id>-<version>.zip."""
        archive = cls(dest / f"{component.id}-{component.version}.zip")
        return archive.write(component.files())

    def write(self, files: dict[str, Path]) -> "Archive":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.path, "w", zipfile.ZIP_STORED) as archive:
            for name in sorted(files):
                member = zipfile.ZipInfo(name, TIMESTAMP)
                member.create_system = 3
                mode = 0o755 if files[name].stat().st_mode & 0o111 else 0o644
                member.external_attr = (0o100000 | mode) << 16
                archive.writestr(member, files[name].read_bytes())
        return self

    def sha256(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()
