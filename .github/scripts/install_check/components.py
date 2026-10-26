"""Components that install themselves and return the checks to run."""

from dataclasses import dataclass
from pathlib import Path

from install_check.checks import (
    Check,
    Done,
    HooksRegistered,
    Override,
    OwnFiles,
    Registered,
    ScriptsExist,
)
from install_check.project import Project
from install_check.repo import FrontMatter, YamlFile


@dataclass(frozen=True)
class Extension:
    """An extension installed from a local directory."""

    source: Path

    def install(self, project: Project) -> list[Check]:
        manifest = YamlFile(self.source / "extension.yml").content()
        ext_id = manifest["extension"]["id"]
        project.run("extension", "add", "--dev", str(self.source))
        provided = manifest.get("provides", {}).get("commands", [])
        commands = tuple(c["name"] for c in provided)
        scripted = tuple(
            c["name"]
            for c in provided
            if FrontMatter(self.source / c["file"]).content().get("scripts")
        )
        checks: list[Check] = [
            Registered(
                project,
                "extensions",
                ext_id,
                str(manifest["extension"]["version"]),
                commands,
            ),
            ScriptsExist(project, ext_id, commands, scripted),
        ]
        if manifest.get("hooks"):
            checks.append(HooksRegistered(project, ext_id, manifest["hooks"]))
        installed = project.path / ".specify" / "extensions" / ext_id
        checks.append(OwnFiles(ext_id, self.source, installed))
        return checks


@dataclass(frozen=True)
class RemoteExtension:
    """An extension installed from a URL."""

    ext_id: str
    url: str

    def install(self, project: Project) -> list[Check]:
        project.run("extension", "add", self.ext_id, "--from", self.url, confirm=True)
        return []


@dataclass(frozen=True)
class Preset:
    """A preset installed from a local directory."""

    manifest: Path

    def install(self, project: Project) -> list[Check]:
        project.run("preset", "add", "--dev", str(self.manifest.parent))
        preset = YamlFile(self.manifest).content()["preset"]
        names = tuple(t["name"] for t in self.commands())
        return [
            Registered(project, "presets", preset["id"], str(preset["version"]), names)
        ]

    def overrides(self, project: Project) -> list[Check]:
        preset_id = YamlFile(self.manifest).content()["preset"]["id"]
        commands = self.commands()
        return [
            *(
                Override(
                    project, preset_id, t["name"], self.manifest.parent / t["file"]
                )
                for t in commands
            ),
            ScriptsExist(
                project,
                preset_id,
                tuple(t["name"] for t in commands),
                tuple(
                    t["name"]
                    for t in commands
                    if FrontMatter(self.manifest.parent / t["file"])
                    .content()
                    .get("scripts")
                ),
            ),
        ]

    def commands(self) -> list[dict]:
        provides = YamlFile(self.manifest).content().get("provides", {})
        return [t for t in provides.get("templates", []) if t.get("type") == "command"]


@dataclass(frozen=True)
class Bundle:
    """A bundle installed from its manifest."""

    manifest: Path
    root: Path

    def install(self, project: Project) -> list[Check]:
        project.run("bundle", "install", str(self.manifest))
        return [Done(f"bundle {self.manifest.relative_to(self.root)} installed")]
