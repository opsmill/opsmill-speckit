"""The full installation of a repo."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from install_check.checks import Check, PlanSetup
from install_check.components import Bundle, Extension, Preset, RemoteExtension
from install_check.project import Project, Specify
from install_check.python import ScriptPython
from install_check.repo import Manifests, Snapshot, YamlFile


@dataclass(frozen=True)
class Installation:
    """Every component of a repo, installed into a fresh project and checked."""

    repo: Path
    specify: Specify

    def verify(self) -> str:
        config = YamlFile(self.repo / ".github" / "install-check.yml").content()
        with tempfile.TemporaryDirectory() as tmp:
            src = Snapshot(self.repo).copy_to(Path(tmp) / "src")
            project = Project(Path(tmp) / "project", self.specify)
            self.init(project)
            self.report(Extension(src).install(project))
            for ext_id, url in (config.get("extensions") or {}).items():
                self.report(RemoteExtension(ext_id, url).install(project))
            presets = [Preset(path) for path in Manifests(src).presets()]
            for preset in presets:
                self.report(preset.install(project))
            # Checked last, so that a later install cannot undo an override unnoticed.
            for preset in presets:
                self.report(preset.overrides(project))
            packages = tuple(config.get("python_packages") or ())
            python = ScriptPython(packages).create(Path(tmp) / "python")
            self.report([PlanSetup(project, python)])
            for path in Manifests(src).bundles():
                self.report(Bundle(path, src).install(project))
        return "every component installed and registered"

    def init(self, project: Project) -> None:
        project.path.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=project.path, check=True)
        print(project.run("version"))
        project.run(
            "init",
            "--here",
            "--integration",
            "claude",
            "--script",
            "sh",
            "--ignore-agent-tools",
            "--force",
        )

    def report(self, checks: list[Check]) -> None:
        for check in checks:
            print(f"ok  {check.verify()}")
