"""What a repo ships: its manifests."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


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
