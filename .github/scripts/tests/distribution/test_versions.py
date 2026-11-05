import subprocess

import pytest
from support import write

from distribution.versions import VersionRaised
from install_check.errors import CheckFailed

PRESET = "preset: {id: p, version: 1.0.0}\n"


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
