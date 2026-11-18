"""Components of an installed bundle and the checks to run on them."""

from dataclasses import dataclass

from install_check.checks import (
    Check,
    Done,
    HooksRegistered,
    Override,
    OwnFiles,
    Pinned,
    Registered,
    ScriptsExist,
    WorkflowLoads,
)
from install_check.errors import CheckFailed
from install_check.project import Project
from repo.components import Bundle, Components, Extension, Preset, Workflow


@dataclass(frozen=True)
class ExtensionInstall:
    """The repo's extension in an installed project."""

    extension: Extension

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
class PresetInstall:
    """A preset of the repo in an installed project."""

    preset: Preset

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
class WorkflowInstall:
    """A workflow of the repo in an installed project."""

    workflow: Workflow

    def checks(self, project: Project) -> list[Check]:
        workflow = self.workflow
        return [
            Pinned(project, "workflows", workflow.id, workflow.version),
            WorkflowLoads(project, workflow.id),
        ]


@dataclass(frozen=True)
class BundleInstall:
    """A bundle of the repo, installed by ID through the catalogs."""

    bundle: Bundle

    def install(self, project: Project) -> list[Check]:
        project.run("bundle", "install", self.bundle.id)
        return [Done(f"bundle {self.bundle.id} installed")]

    def checks(self, project: Project) -> list[Check]:
        """What the bundle installs, with the repo's preset overrides checked last."""
        repo = Components(self.bundle.root)
        extension = repo.extension()
        presets = {preset.id: PresetInstall(preset) for preset in repo.presets()}
        workflows = {w.id: WorkflowInstall(w) for w in repo.workflows()}
        references = self.references()
        checks: list[Check] = []
        for kind, ref in references:
            if kind == "extensions" and ref["id"] == extension.id:
                checks.extend(ExtensionInstall(extension).checks(project))
            elif kind == "presets" and ref["id"] in presets:
                checks.extend(presets[ref["id"]].checks(project))
            elif kind == "workflows" and ref["id"] in workflows:
                checks.extend(workflows[ref["id"]].checks(project))
            else:
                checks.append(
                    Pinned(
                        project,
                        kind,
                        ref["id"],
                        str(ref["version"]),
                        bool(ref.get("source")),
                    )
                )
        for kind, ref in references:
            if kind == "presets" and ref["id"] in presets:
                checks.extend(presets[ref["id"]].overrides(project))
        return checks

    def references(self, seen: tuple[str, ...] = ()) -> list[tuple[str, dict]]:
        """The extensions and presets it installs, those of referenced bundles first."""
        if self.bundle.id in seen:
            raise CheckFailed(
                f"bundle {self.bundle.id} references itself: {' -> '.join(seen)}"
            )
        refs: list[tuple[str, dict]] = []
        for kind, ref in self.bundle.references():
            if kind == "bundles":
                referenced = BundleInstall(self.find(ref["id"]))
                refs.extend(referenced.references((*seen, self.bundle.id)))
            else:
                refs.append((kind, ref))
        return refs

    def find(self, bundle_id: str) -> Bundle:
        for bundle in Components(self.bundle.root).bundles():
            if bundle.id == bundle_id:
                return bundle
        raise CheckFailed(
            f"bundle {self.bundle.id} references {bundle_id}, which the repo does not ship"
        )
