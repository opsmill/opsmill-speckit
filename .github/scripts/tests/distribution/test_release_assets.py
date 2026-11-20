import subprocess

import pytest
from support import write

from distribution.archives import build
from distribution.catalogs import Catalogs, Location
from install_check.errors import CheckFailed
from repo.components import Components


def test_fails_when_a_zip_listed_for_the_release_has_another_sha256(tmp_path):
    repo, catalog = tmp_path / "repo", tmp_path / "catalog"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    write(repo / "extension.yml", "extension: {id: x, version: 1.0.0}\n")
    location = Location("https://c/", "https://r/1.0.0/")
    Catalogs(catalog).publish(build(Components(repo), tmp_path / "listed"), location)
    write(repo / "commands" / "a.md", "changed after the release pull request")

    with pytest.raises(CheckFailed, match="x-1.0.0.zip: its sha256 is not the one"):
        Catalogs(catalog).assets(build(Components(repo), tmp_path / "built"), location)
