# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=24", "pyyaml>=6"]
# ///
"""Install this repo's spec-kit components into a fresh project and check them.

Everything comes from the repo itself, so the check needs no update when a
component, command, hook or preset is added:

- the extension from ``extension.yml``, every preset from
  ``presets/*/preset.yml``, and the bundle from ``bundle.yml`` once it exists;
- the extensions our presets depend on from ``.github/install-check.yml``.

The components are installed from the files git tracks (what a tag archive
holds), then checked against the registries spec-kit writes in
``.specify/``: versions, registered commands, hooks, and files that must stay
out of the installed extension (``.extensionignore`` plus ``FOREIGN_PATHS``).

Usage:
    uv run .github/scripts/check_install.py              # install and check
    uv run .github/scripts/check_install.py min-version  # oldest spec-kit to test

Runs the ``specify`` on PATH; set SPECIFY to use another one, for example
    SPECIFY="uvx --from specify-cli==1.2.3 specify"
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from packaging.specifiers import SpecifierSet
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / ".github" / "install-check.yml"


class CheckFailed(Exception):
    pass


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def manifests(root: Path) -> list[Path]:
    paths = [root / "extension.yml", *sorted(root.glob("presets/*/preset.yml"))]
    if (root / "bundle.yml").exists():
        paths.append(root / "bundle.yml")
    return paths


def min_speckit_version(root: Path) -> Version:
    """Highest lower bound declared in requires.speckit_version across manifests."""
    bounds = []
    for path in manifests(root):
        spec = load_yaml(path).get("requires", {}).get("speckit_version")
        if not spec:
            continue
        for item in SpecifierSet(spec):
            if item.operator in (">=", "==", "~="):
                bounds.append(Version(item.version))
    if not bounds:
        raise CheckFailed("no manifest declares requires.speckit_version")
    return max(bounds)


class Project:
    def __init__(self, path: Path, specify: list[str]) -> None:
        self.path = path
        self.specify = specify

    def run(self, *args: str, confirm: bool = False) -> str:
        cmd = [*self.specify, *args]
        print("$", shlex.join(cmd), flush=True)
        result = subprocess.run(
            cmd,
            check=False,
            cwd=self.path,
            input="y\n" if confirm else "",
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise CheckFailed(
                f"{shlex.join(cmd)} exited with {result.returncode}\n{result.stdout}{result.stderr}"
            )
        return result.stdout

    def integration(self) -> str:
        return json.loads((self.path / ".specify" / "integration.json").read_text())[
            "integration"
        ]

    def registry(self, kind: str) -> dict:
        path = self.path / ".specify" / kind / ".registry"
        return json.loads(path.read_text())[kind] if path.exists() else {}


def tracked_copy(root: Path, dest: Path) -> Path:
    """Copy the files git tracks or would track, i.e. what a tag archive holds."""
    files = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\0")
    for name in filter(None, files):
        src = root / name
        if src.is_file():
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
    return dest


# Never part of the installed extension, whatever .extensionignore says: other
# components' manifests (presets and bundles install on their own) and git or
# CI files.
FOREIGN_PATHS = ["preset.yml", "bundle.yml", ".git", ".github"]


def ignored_paths(ext_root: Path, installed: Path) -> list[str]:
    """Paths that should not be in the installed extension but are."""
    patterns = list(FOREIGN_PATHS)
    ignore = ext_root / ".extensionignore"
    if ignore.exists():
        patterns += ignore.read_text().splitlines()
    leaked = set()
    for line in patterns:
        pattern = line.strip().rstrip("/")
        if not pattern or pattern.startswith(("#", "!")):
            continue
        # Patterns without "/" match at any depth, like .gitignore.
        matches = (
            installed.glob(pattern) if "/" in pattern else installed.rglob(pattern)
        )
        leaked.update(str(p.relative_to(installed)) for p in matches)
    return sorted(leaked)


def check_registered(
    kind: str,
    component_id: str,
    manifest: dict,
    expected_commands: list[str],
    project: Project,
) -> None:
    entry = project.registry(kind).get(component_id)
    if entry is None:
        raise CheckFailed(f"{component_id} is not in .specify/{kind}/.registry")
    version = str(manifest["version"])
    if str(entry.get("version")) != version:
        raise CheckFailed(
            f"{component_id}: registry has version {entry.get('version')}, manifest has {version}"
        )
    if not entry.get("enabled", True):
        raise CheckFailed(f"{component_id} is installed but disabled")
    registered = set(
        entry.get("registered_commands", {}).get(project.integration(), [])
    )
    missing = sorted(set(expected_commands) - registered)
    if missing:
        raise CheckFailed(
            f"{component_id}: commands not registered for {project.integration()}: {', '.join(missing)}"
        )
    print(
        f"ok  {component_id} v{version}: {len(expected_commands)} commands registered"
    )


def check_hooks(ext_id: str, manifest: dict, project: Project) -> None:
    declared = manifest.get("hooks") or {}
    if not declared:
        return
    registered = (
        load_yaml(project.path / ".specify" / "extensions.yml").get("hooks") or {}
    )
    for event, hook in declared.items():
        entries = registered.get(event) or []
        if not any(
            e.get("extension") == ext_id and e.get("command") == hook["command"]
            for e in entries
        ):
            raise CheckFailed(
                f"{ext_id}: hook {event} -> {hook['command']} is not in .specify/extensions.yml"
            )
    print(f"ok  {ext_id}: {len(declared)} hooks registered")


def check(specify: list[str]) -> None:
    config = load_yaml(CONFIG) if CONFIG.exists() else {}
    with tempfile.TemporaryDirectory() as tmp:
        src = tracked_copy(REPO_ROOT, Path(tmp) / "src")
        project = Project(Path(tmp) / "project", specify)
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

        ext = load_yaml(src / "extension.yml")
        ext_id = ext["extension"]["id"]
        project.run("extension", "add", "--dev", str(src))
        ext_commands = [c["name"] for c in ext.get("provides", {}).get("commands", [])]
        check_registered("extensions", ext_id, ext["extension"], ext_commands, project)
        check_hooks(ext_id, ext, project)
        leaked = ignored_paths(src, project.path / ".specify" / "extensions" / ext_id)
        if leaked:
            raise CheckFailed(
                f"{ext_id}: paths that do not belong to the extension were installed: {', '.join(leaked)}"
            )
        print(f"ok  {ext_id}: only extension files installed")

        for dep_id, url in (config.get("extensions") or {}).items():
            project.run("extension", "add", dep_id, "--from", url, confirm=True)

        for path in sorted(src.glob("presets/*/preset.yml")):
            preset = load_yaml(path)
            project.run("preset", "add", "--dev", str(path.parent))
            templates = preset.get("provides", {}).get("templates", [])
            commands = [t["name"] for t in templates if t.get("type") == "command"]
            check_registered(
                "presets", preset["preset"]["id"], preset["preset"], commands, project
            )

        if (src / "bundle.yml").exists():
            # The components above are installed from this commit, so the
            # bundle install checks that its pins match them.
            project.run("bundle", "install", str(src / "bundle.yml"))
            print("ok  bundle installed")


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    try:
        if command == "min-version":
            print(min_speckit_version(REPO_ROOT))
        elif command == "check":
            check(shlex.split(os.environ.get("SPECIFY", "specify")))
            print("OK: every component installed and registered")
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except CheckFailed as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
