"""Checks on an installed project."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Protocol

from install_check.errors import CheckFailed
from install_check.project import AgentFile, Project


class Check(Protocol):
    def verify(self) -> str:
        """Raise CheckFailed, or describe what passed."""
        ...


@dataclass(frozen=True)
class Done:
    """A step with nothing left to check."""

    message: str

    def verify(self) -> str:
        return self.message


@dataclass(frozen=True)
class Registered:
    """A component is registered and enabled, at its version, with its commands."""

    project: Project
    kind: str
    component_id: str
    version: str
    commands: tuple[str, ...]

    def verify(self) -> str:
        entry = self.project.registry(self.kind).entry(self.component_id)
        if str(entry.get("version")) != self.version:
            raise CheckFailed(
                f"{self.component_id}: registry has version {entry.get('version')}, manifest has {self.version}"
            )
        if not entry.get("enabled", True):
            raise CheckFailed(f"{self.component_id} is installed but disabled")
        integration = self.project.integration()
        registered = set(entry.get("registered_commands", {}).get(integration, []))
        missing = sorted(set(self.commands) - registered)
        if missing:
            raise CheckFailed(
                f"{self.component_id}: commands not registered for {integration}: {', '.join(missing)}"
            )
        return f"{self.component_id} v{self.version}: {len(self.commands)} commands registered"


@dataclass(frozen=True)
class HooksRegistered:
    """Every hook an extension declares is registered."""

    project: Project
    ext_id: str
    declared: dict

    def verify(self) -> str:
        registered = self.project.hooks()
        for event, hook in self.declared.items():
            if not any(
                e.get("extension") == self.ext_id
                and e.get("command") == hook["command"]
                for e in registered.get(event) or []
            ):
                raise CheckFailed(
                    f"{self.ext_id}: hook {event} -> {hook['command']} is not in .specify/extensions.yml"
                )
        return f"{self.ext_id}: {len(self.declared)} hooks registered"


@dataclass(frozen=True)
class OwnFiles:
    """The installed extension holds only its own files."""

    # Paths that never belong to an extension, whatever .extensionignore says.
    FOREIGN: ClassVar[tuple[str, ...]] = ("preset.yml", "bundle.yml", ".github")

    ext_id: str
    source: Path
    installed: Path

    def verify(self) -> str:
        leaked = sorted({str(p.relative_to(self.installed)) for p in self.matches()})
        if leaked:
            raise CheckFailed(
                f"{self.ext_id}: paths that do not belong to the extension were installed: {', '.join(leaked)}"
            )
        return f"{self.ext_id}: only extension files installed"

    def matches(self) -> Iterator[Path]:
        for line in self.patterns():
            pattern = line.strip().rstrip("/")
            if not pattern or pattern.startswith(("#", "!")):
                continue
            # As in .gitignore, a pattern without "/" matches at any depth.
            yield from (
                self.installed.glob(pattern)
                if "/" in pattern
                else self.installed.rglob(pattern)
            )

    def patterns(self) -> list[str]:
        ignore = self.source / ".extensionignore"
        lines = ignore.read_text().splitlines() if ignore.exists() else []
        return [*self.FOREIGN, *lines]


@dataclass(frozen=True)
class ScriptsExist:
    """Every script that a component's commands run exists in the project."""

    # The project is initialized with --script sh, so commands run .sh scripts.
    SCRIPT: ClassVar[re.Pattern] = re.compile(r"\.specify/[\w./-]+\.sh")

    project: Project
    component_id: str
    commands: tuple[str, ...]

    def verify(self) -> str:
        found, missing = set(), set()
        for command in self.commands:
            text = AgentFile(self.project, command).path().read_text()
            if "{SCRIPT}" in text:
                raise CheckFailed(
                    f"{self.component_id}: {command} still holds the {{SCRIPT}} placeholder"
                )
            for script in self.SCRIPT.findall(text):
                found.add(script)
                if not (self.project.path / script).is_file():
                    missing.add(f"{script} ({command})")
        if missing:
            raise CheckFailed(
                f"{self.component_id}: commands run scripts that do not exist: {', '.join(sorted(missing))}"
            )
        return f"{self.component_id}: {len(found)} scripts found"


@dataclass(frozen=True)
class Override:
    """A command that a preset replaces holds the preset's text."""

    project: Project
    preset_id: str
    command: str
    source: Path

    def verify(self) -> str:
        agent_file = AgentFile(self.project, self.command).path()
        installed = {line.strip() for line in agent_file.read_text().splitlines()}
        probes = self.probes()
        if not probes:
            raise CheckFailed(
                f"{self.preset_id}: {self.command}: no line of the preset can be checked"
            )
        missing = [line for line in probes if line not in installed]
        if missing:
            raise CheckFailed(
                f"{self.preset_id}: {self.command} does not use the preset's text ({len(missing)} of {len(probes)} lines missing, "
                f"first: {missing[0][:80]!r})"
            )
        return f"{self.preset_id}: {self.command} uses the preset's text"

    def probes(self) -> list[str]:
        text = self.source.read_text()
        body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.DOTALL)
        # Lines with placeholders change on install, so they are skipped.
        return [
            line.strip()
            for line in body.splitlines()
            if len(line.strip()) >= 30 and not re.search(r"[${}]", line)
        ]
