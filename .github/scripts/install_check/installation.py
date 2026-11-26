"""The full installation of a repo."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from distribution.catalogs import Location
from install_check.catalogs import Declaration, LocalRelease
from install_check.checks import Check, PlanSetup, PythonHooks
from install_check.components import BundleInstall
from install_check.errors import CheckFailed
from install_check.project import Project, Specify
from install_check.python import ScriptPython
from repo.components import Components
from repo.files import YamlFile


@dataclass(frozen=True)
class Installation:
    """Each bundle of a repo, installed by ID into a fresh project and checked.

    The bundles resolve their components through the repo's catalogs, served
    on localhost with the zips built from the working tree.
    """

    repo: Path
    specify: Specify

    def verify(self) -> str:
        config = YamlFile(self.repo / ".github" / "install-check.yml").content()
        bundles = Components(self.repo).bundles()
        if not bundles:
            raise CheckFailed("the repo ships no bundle in bundles/")
        with tempfile.TemporaryDirectory() as tmp:
            packages = tuple(config.get("python_packages") or ())
            python = ScriptPython(packages).create(Path(tmp) / "python")
            with LocalRelease(self.repo, Path(tmp) / "release").serve() as location:
                for bundle in bundles:
                    project = Project(Path(tmp) / bundle.id, self.specify)
                    self.init(project, location)
                    install = BundleInstall(bundle)
                    self.report(install.install(project))
                    self.report(install.checks(project))
                    self.report(
                        [PlanSetup(project, python), PythonHooks(project, python)]
                    )
        return f"bundles installed and checked: {', '.join(b.id for b in bundles)}"

    def init(self, project: Project, location: Location) -> None:
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
        Declaration(self.repo).write(project, location)

    def report(self, checks: list[Check]) -> None:
        for check in checks:
            print(f"ok  {check.verify()}")
