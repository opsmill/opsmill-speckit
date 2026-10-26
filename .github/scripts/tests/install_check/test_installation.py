import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from install_check.errors import CheckFailed
from install_check.installation import Installation


@dataclass(frozen=True)
class FakeSpeckit:
    """A spec-kit that registers components and writes skills for extension commands only."""

    def run(self, cwd: Path, *args: str, confirm: bool = False) -> str:
        specify = cwd / ".specify"
        if args[0] == "init":
            specify.mkdir()
            (specify / "integration.json").write_text('{"integration": "claude"}')
        elif args[:3] == ("extension", "add", "--dev"):
            manifest = yaml.safe_load((Path(args[3]) / "extension.yml").read_text())
            commands = [c["name"] for c in manifest["provides"]["commands"]]
            self.register(specify, "extensions", manifest["extension"], commands)
            for command in commands:
                skill = cwd / ".claude" / "skills" / command.replace(".", "-")
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(f"The {command} command.\n")
        elif args[:3] == ("preset", "add", "--dev"):
            manifest = yaml.safe_load((Path(args[3]) / "preset.yml").read_text())
            templates = manifest["provides"]["templates"]
            self.register(
                specify, "presets", manifest["preset"], [t["name"] for t in templates]
            )
        return ""

    def register(
        self, specify: Path, kind: str, component: dict, commands: list[str]
    ) -> None:
        path = specify / kind / ".registry"
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = json.loads(path.read_text())[kind] if path.exists() else {}
        entries[component["id"]] = {
            "version": component["version"],
            "registered_commands": {"claude": commands},
        }
        path.write_text(json.dumps({kind: entries}))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo with an extension and a preset that replaces a command."""
    root = tmp_path / "repo"
    files = {
        "extension.yml": "extension: {id: opsmill, version: 1.0.0}\n"
        "provides: {commands: [{name: speckit.opsmill.summary}]}\n",
        "presets/r/preset.yml": "preset: {id: r, version: 2.0.0}\n"
        "provides: {templates: [{type: command, name: speckit.plan, file: plan.md}]}\n",
    }
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def test_fails_when_a_preset_override_did_not_apply(repo):
    with pytest.raises(CheckFailed, match="speckit.plan: no skill or command file"):
        Installation(repo, FakeSpeckit()).verify()
