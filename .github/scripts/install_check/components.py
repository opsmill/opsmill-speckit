"""How the install check installs each component, and the checks to run on it."""

from dataclasses import dataclass

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
from repo.components import Bundle, Extension, Preset


@dataclass(frozen=True)
class ExtensionInstall:
    """The repo's extension, installed from a local directory."""

    extension: Extension

    def install(self, project: Project) -> list[Check]:
        # Reading the manifest first fails at once on a malformed extension.yml.
        checks = self.checks(project)
        project.run("extension", "add", "--dev", str(self.extension.folder))
        return checks

    def checks(self, project: Project) -> list[Check]:
        extension = self.extension
        commands = tuple(c["name"] for c in extension.commands())
        checks: list[Check] = [
            Registered(
                project, "extensions", extension.id, extension.version, commands
            ),
            ScriptsExist(project, extension.id, commands, extension.scripted()),
        ]
        if extension.hooks():
            checks.append(HooksRegistered(project, extension.id, extension.hooks()))
        installed = project.path / ".specify" / "extensions" / extension.id
        checks.append(OwnFiles(extension.id, extension.folder, installed))
        return checks


@dataclass(frozen=True)
class RemoteExtension:
    """An extension the repo does not ship: from a URL, or bundled with spec-kit."""

    ext_id: str
    url: str | None

    def install(self, project: Project) -> list[Check]:
        # Some spec-kit releases install the bundled git extension on init.
        if project.registry("extensions").has(self.ext_id):
            return [Done(f"{self.ext_id} already installed")]
        if self.url:
            project.run(
                "extension", "add", self.ext_id, "--from", self.url, confirm=True
            )
        else:
            project.run("extension", "add", self.ext_id)
        return []


@dataclass(frozen=True)
class PresetInstall:
    """A preset of the repo, installed from its folder."""

    preset: Preset

    def install(self, project: Project) -> list[Check]:
        project.run("preset", "add", "--dev", str(self.preset.folder))
        return self.checks(project)

    def checks(self, project: Project) -> list[Check]:
        preset = self.preset
        names = tuple(t["name"] for t in preset.commands())
        return [Registered(project, "presets", preset.id, preset.version, names)]

    def overrides(self, project: Project) -> list[Check]:
        """The preset's commands replace the ones they override."""
        preset = self.preset
        commands = preset.commands()
        return [
            *(
                Override(project, preset.id, t["name"], preset.folder / t["file"])
                for t in commands
            ),
            ScriptsExist(
                project,
                preset.id,
                tuple(t["name"] for t in commands),
                preset.scripted(),
            ),
        ]


@dataclass(frozen=True)
class BundleInstall:
    """A bundle of the repo, installed from its manifest."""

    bundle: Bundle

    def install(self, project: Project) -> list[Check]:
        project.run("bundle", "install", str(self.bundle.manifest))
        manifest = self.bundle.manifest.relative_to(self.bundle.root)
        return [Done(f"bundle {manifest} installed")]
