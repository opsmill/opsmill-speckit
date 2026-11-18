"""The components that a repo ships: its extension, presets, workflows and bundles."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from repo.files import FrontMatter, Snapshot, YamlFile


@dataclass(frozen=True)
class Component(ABC):
    """A component of a repo, described by its manifest."""

    # The name of this kind of component in catalogs and in bundle manifests.
    kind: ClassVar[str]
    # The manifest key that holds the component's id and version.
    key: ClassVar[str]
    # The field of its catalog entry that holds the URL of its zip.
    url_field: ClassVar[str] = "download_url"

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

    def files(self) -> dict[str, Path]:
        """The files of its release zip, by name, with the manifest at the root."""
        folder = self.folder.relative_to(self.root).as_posix() + "/"
        return {
            name.removeprefix(folder): self.root / name
            for name in Snapshot(self.root).files()
            if name.startswith(folder)
        }

    def commands(self) -> list[dict]:
        """The commands it provides, each with a `name` and a `file` in its folder."""
        return []

    def requirements(self) -> dict:
        """What its catalog entry lists under `requires`."""
        speckit = (self.content().get("requires") or {}).get("speckit_version")
        return {"speckit_version": str(speckit)} if speckit else {}

    @abstractmethod
    def counts(self) -> dict[str, int]:
        """What it provides, counted as its catalog entry lists it."""

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
    # The extension is the repo root minus these files, as when spec-kit
    # installs it from a directory.
    IGNORE: ClassVar[str] = ".extensionignore"

    def files(self) -> dict[str, Path]:
        snapshot = Snapshot(self.root)
        ignored = (
            set(snapshot.files(f"--exclude-from={self.IGNORE}", "--ignored"))
            if (self.root / self.IGNORE).is_file()
            else set()
        )
        return {
            name: self.root / name
            for name in snapshot.files()
            if name not in ignored and name != self.IGNORE
        }

    def commands(self) -> list[dict]:
        return list((self.content().get("provides") or {}).get("commands") or [])

    def hooks(self) -> dict:
        return self.content().get("hooks") or {}

    def counts(self) -> dict[str, int]:
        return {"commands": len(self.commands()), "hooks": len(self.hooks())}


class Preset(Component):
    """A preset of the repo, in presets/<id>/."""

    kind = "presets"
    key = "preset"

    def templates(self) -> list[dict]:
        return list((self.content().get("provides") or {}).get("templates") or [])

    def commands(self) -> list[dict]:
        return [t for t in self.templates() if t.get("type") == "command"]

    def counts(self) -> dict[str, int]:
        commands = len(self.commands())
        return {"commands": commands, "templates": len(self.templates()) - commands}


class Workflow(Component):
    """A Spec Kit workflow of the repo, in workflows/<id>/."""

    kind = "workflows"
    key = "workflow"
    url_field = "url"

    def steps(self) -> list[dict]:
        return list(self.content().get("steps") or [])

    def counts(self) -> dict[str, int]:
        """A workflow catalog entry lists no counts."""
        return {}

    def requirements(self) -> dict:
        """All of `requires`: Spec Kit refuses a workflow whose entry lists another."""
        return dict(self.content().get("requires") or {})


class Bundle(Component):
    """A bundle of the repo, in bundles/<id>/."""

    kind = "bundles"
    key = "bundle"

    def counts(self) -> dict[str, int]:
        provides = self.content().get("provides") or {}
        return {
            kind: len(provides.get(kind) or [])
            for kind in ("bundles", "extensions", "presets", "steps", "workflows")
        }

    def references(self) -> list[tuple[str, dict]]:
        """The bundles, extensions, presets and workflows it pins, each with its kind."""
        provides = self.content().get("provides") or {}
        return [
            (kind, ref)
            for kind in ("bundles", "extensions", "presets", "workflows")
            for ref in provides.get(kind) or []
        ]


@dataclass(frozen=True)
class Components:
    """Every component of a repo, extension first and bundles last."""

    root: Path

    def __iter__(self) -> Iterator[Component]:
        yield self.extension()
        yield from self.presets()
        yield from self.workflows()
        yield from self.bundles()

    def extension(self) -> Extension:
        return Extension(self.root, self.root / "extension.yml")

    def presets(self) -> list[Preset]:
        paths = sorted(self.root.glob("presets/*/preset.yml"))
        return [Preset(self.root, path) for path in paths]

    def workflows(self) -> list[Workflow]:
        paths = sorted(self.root.glob("workflows/*/workflow.yml"))
        return [Workflow(self.root, path) for path in paths]

    def bundles(self) -> list[Bundle]:
        paths = sorted(self.root.glob("bundles/*/bundle.yml"))
        return [Bundle(self.root, path) for path in paths]
