import subprocess

import pytest
from support import write

from distribution.versions import PinsMatch, VersionRaised
from install_check.errors import CheckFailed

PRESET = "preset: {id: p, version: 1.0.0}\n"
BUNDLE = (
    "bundle: {id: b, version: 1.0.0}\n"
    "provides: {presets: [{id: p, version: %s, source: opsmill}]}\n"
)


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    write(root / "extension.yml", "extension: {id: x, version: 1.0.0}\n")
    write(root / "presets" / "p" / "preset.yml", PRESET)
    git(root, "add", ".")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    return root


class TestVersionRaised:
    def test_fails_on_a_change_without_a_higher_version(self, repo):
        write(repo / "presets" / "p" / "command.md", "changed")
        with pytest.raises(
            CheckFailed, match="p changed since HEAD: raise its version above 1.0.0"
        ):
            VersionRaised(repo, "HEAD").verify()


class TestPinsMatch:
    def test_fails_on_a_pin_that_is_not_the_manifest_version(self, repo):
        write(repo / "bundles" / "b" / "bundle.yml", BUNDLE % "0.9.0")
        with pytest.raises(CheckFailed, match="b pins p 0.9.0, its manifest has 1.0.0"):
            PinsMatch(repo).verify()

    def test_leaves_a_pin_from_another_catalog_to_spec_kit(self, repo):
        write(
            repo / "bundles" / "b" / "bundle.yml",
            "bundle: {id: b, version: 1.0.0}\n"
            "provides:\n"
            "  extensions: [{id: x, version: 1.0.0, source: opsmill},"
            " {id: git, version: 1.0.1, source: default}]\n"
            "  presets: [{id: p, version: 1.0.0, source: opsmill}]\n",
        )
        PinsMatch(repo).verify()

    def test_fails_on_a_component_in_no_bundle(self, repo):
        write(repo / "bundles" / "b" / "bundle.yml", BUNDLE % "1.0.0")
        with pytest.raises(CheckFailed, match="^x is in no bundle$"):
            PinsMatch(repo).verify()
