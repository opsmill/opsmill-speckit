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
    """A spec-kit that installs a bundle from the repo's manifests, and writes
    skills for extension commands only."""

    repo: Path

    def run(self, cwd: Path, *args: str, confirm: bool = False) -> str:
        specify = cwd / ".specify"
        if args[0] == "init":
            specify.mkdir()
            (specify / "integration.json").write_text('{"integration": "claude"}')
        elif args[:2] == ("bundle", "install"):
            manifest = yaml.safe_load((self.repo / "extension.yml").read_text())
            commands = [c["name"] for c in manifest["provides"]["commands"]]
            self.register(specify, "extensions", manifest["extension"], commands)
            for command in commands:
                skill = cwd / ".claude" / "skills" / command.replace(".", "-")
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(f"The {command} command.\n")
            for path in self.repo.glob("presets/*/preset.yml"):
                preset = yaml.safe_load(path.read_text())
                templates = [t["name"] for t in preset["provides"]["templates"]]
                self.register(specify, "presets", preset["preset"], templates)
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


CATALOGS = "https://raw.githubusercontent.com/opsmill/opsmill-speckit/main/catalog/"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo with an extension, a preset that replaces a command, and a bundle."""
    root = tmp_path / "repo"
    files = {
        "extension.yml": "extension: {id: opsmill, version: 1.0.0}\n"
        "provides: {commands: [{name: speckit.opsmill.summary, file: commands/summary.md}]}\n",
        "commands/summary.md": "Summarize the session.\n",
        "presets/r/preset.yml": "preset: {id: r, version: 2.0.0}\n"
        "provides: {templates: [{type: command, name: speckit.plan, file: plan.md}]}\n",
        "bundles/b/bundle.yml": "bundle: {id: b, version: 1.0.0}\n"
        "provides:\n"
        "  extensions: [{id: opsmill, version: 1.0.0, source: opsmill}]\n"
        "  presets: [{id: r, version: 2.0.0, source: opsmill}]\n",
        "catalog/specify/bundle-catalogs.yml": f"catalogs: [{{id: opsmill, url: {CATALOGS}bundle-catalog.json}}]\n",
    }
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def test_fails_when_a_preset_override_did_not_apply(repo):
    with pytest.raises(CheckFailed, match="speckit.plan: no skill or command file"):
        Installation(repo, FakeSpeckit(repo)).verify()
