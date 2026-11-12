"""The components that a repo ships: its extension, its presets and its bundles."""

from abc import ABC
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from repo.files import FrontMatter, YamlFile


@dataclass(frozen=True)
class Component(ABC):
    """A component of a repo, described by its manifest."""

    # The name of this kind of component in catalogs and in bundle manifests.
    kind: ClassVar[str]
    # The manifest key that holds the component's id and version.
    key: ClassVar[str]

    root: Path
    manifest: Path

    def content(self) -> dict:
        return YamlFile(self.manifest).content()

    def info(self) -> dict:
        return self.content()[self.key]

    @property
    def id(self) -> str:
        return str(self.info()["id"])

    @property
    def version(self) -> str:
        return str(self.info()["version"])

    @property
    def folder(self) -> Path:
        return self.manifest.parent

    def commands(self) -> list[dict]:
        """The commands it provides, each with a `name` and a `file` in its folder."""
        return []

    def scripted(self) -> tuple[str, ...]:
        """The commands whose file declares scripts in its front matter."""
        return tuple(
            command["name"]
            for command in self.commands()
            if FrontMatter(self.folder / command["file"]).content().get("scripts")
        )


class Extension(Component):
    """The repo's extension, whose folder is the repo root."""

    kind = "extensions"
    key = "extension"

    def commands(self) -> list[dict]:
        return list((self.content().get("provides") or {}).get("commands") or [])

    def hooks(self) -> dict:
        return self.content().get("hooks") or {}


class Preset(Component):
    """A preset of the repo, in presets/<id>/."""

    kind = "presets"
    key = "preset"

    def templates(self) -> list[dict]:
        return list((self.content().get("provides") or {}).get("templates") or [])

    def commands(self) -> list[dict]:
        return [t for t in self.templates() if t.get("type") == "command"]


class Bundle(Component):
    """A bundle of the repo, in bundles/<id>/ or at the repo root."""

    kind = "bundles"
    key = "bundle"


@dataclass(frozen=True)
class Components:
    """Every component of a repo, extension first and bundles last."""

    root: Path

    def __iter__(self) -> Iterator[Component]:
        yield self.extension()
        yield from self.presets()
        yield from self.bundles()

    def extension(self) -> Extension:
        return Extension(self.root, self.root / "extension.yml")

    def presets(self) -> list[Preset]:
        paths = sorted(self.root.glob("presets/*/preset.yml"))
        return [Preset(self.root, path) for path in paths]

    def bundles(self) -> list[Bundle]:
        paths = [self.root / "bundle.yml", *self.root.glob("bundles/*/bundle.yml")]
        return [
            Bundle(self.root, path) for path in sorted(p for p in paths if p.exists())
        ]
