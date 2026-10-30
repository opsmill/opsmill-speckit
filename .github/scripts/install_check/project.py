"""The spec-kit project that components are installed into."""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from install_check.errors import CheckFailed
from install_check.repo import YamlFile


@dataclass(frozen=True)
class Specify:
    """The specify command line."""

    argv: tuple[str, ...]

    def run(self, cwd: Path, *args: str, confirm: bool = False) -> str:
        cmd = [*self.argv, *args]
        print("$", shlex.join(cmd), flush=True)
        result = subprocess.run(
            cmd,
            check=False,
            cwd=cwd,
            input="y\n" if confirm else "",
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise CheckFailed(
                f"{shlex.join(cmd)} exited with {result.returncode}\n{result.stdout}{result.stderr}"
            )
        return result.stdout


@dataclass(frozen=True)
class Project:
    """A spec-kit project on disk."""

    path: Path
    specify: Specify

    def run(self, *args: str, confirm: bool = False) -> str:
        return self.specify.run(self.path, *args, confirm=confirm)

    def integration(self) -> str:
        integration = self.path / ".specify" / "integration.json"
        return json.loads(integration.read_text())["integration"]

    def registry(self, kind: str) -> Registry:
        return Registry(self.path / ".specify" / kind / ".registry", kind)

    def hooks(self) -> dict:
        extensions = YamlFile(self.path / ".specify" / "extensions.yml")
        return extensions.content().get("hooks") or {}


@dataclass(frozen=True)
class Registry:
    """The installed components of one kind."""

    path: Path
    kind: str

    def has(self, component_id: str) -> bool:
        return component_id in self.entries()

    def entry(self, component_id: str) -> dict:
        entries = self.entries()
        if component_id not in entries:
            raise CheckFailed(
                f"{component_id} is not in .specify/{self.kind}/.registry"
            )
        return entries[component_id]

    def entries(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())[self.kind]


@dataclass(frozen=True)
class AgentFile:
    """The file the agent reads for a command."""

    project: Project
    command: str

    def path(self) -> Path:
        root = self.project.path
        skill = self.command.replace(".", "-")
        candidates = [p for p in root.rglob("SKILL.md") if p.parent.name == skill]
        candidates += root.rglob(f"{self.command}.md")
        candidates = [
            p for p in candidates if ".specify" not in p.relative_to(root).parts
        ]
        if not candidates:
            raise CheckFailed(f"{self.command}: no skill or command file for the agent")
        return candidates[0]
