import subprocess
from pathlib import Path

import pytest
from packaging.version import Version
from support import write

from install_check.errors import CheckFailed
from install_check.repo import Manifests, Snapshot, SpeckitFloor


def requiring(root: Path, name: str, spec: str) -> Path:
    return write(root / name, f"requires:\n  speckit_version: {spec!r}\n")


class TestManifests:
    def test_finds_bundles_at_the_root_and_in_bundles(self, tmp_path):
        write(tmp_path / "bundles" / "x" / "bundle.yml", "")
        write(tmp_path / "bundle.yml", "")
        assert Manifests(tmp_path).bundles() == [
            tmp_path / "bundle.yml",
            tmp_path / "bundles" / "x" / "bundle.yml",
        ]


class TestSpeckitFloor:
    def test_is_the_highest_lower_bound_across_manifests(self, tmp_path):
        requiring(tmp_path, "extension.yml", ">=0.8.0")
        requiring(tmp_path, "presets/a/preset.yml", ">=1.2,<2")
        assert SpeckitFloor(Manifests(tmp_path)).version() == Version("1.2")

    def test_refuses_a_range_without_an_inclusive_lower_bound(self, tmp_path):
        requiring(tmp_path, "extension.yml", "<2")
        with pytest.raises(CheckFailed, match="extension.yml: .* use >="):
            SpeckitFloor(Manifests(tmp_path)).version()


class TestSnapshot:
    def test_copies_tracked_and_unignored_files_only(self, tmp_path):
        repo = tmp_path / "repo"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        write(repo / ".gitignore", "ignored.txt\n")
        write(repo / "tracked" / "a.md", "a")
        write(repo / "untracked.md", "b")
        write(repo / "ignored.txt", "c")
        subprocess.run(["git", "-C", str(repo), "add", "tracked"], check=True)

        dest = Snapshot(repo).copy_to(tmp_path / "copy")

        assert sorted(
            p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()
        ) == [
            ".gitignore",
            "tracked/a.md",
            "untracked.md",
        ]
