import subprocess

import pytest
from support import write

from distribution.archives import build
from distribution.catalogs import Catalogs, Location
from install_check.errors import CheckFailed
from repo.components import Components


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    write(root / "extension.yml", "extension: {id: x, version: 1.0.0}\n")
    write(root / "presets" / "p" / "preset.yml", "preset: {id: p, version: 1.0.0}\n")
    return root


def release(version: str) -> Location:
    return Location("https://c/", f"https://r/{version}/")


def publish(repo, catalog, version: str, published: tuple[str, ...] = ()) -> None:
    archives = build(Components(repo), repo.parent / "listed" / version)
    Catalogs(catalog).publish(
        archives, release(version), tuple(release(v).archives for v in published)
    )


def assets(repo, catalog, version: str) -> list[str]:
    archives = build(Components(repo), repo.parent / "built" / version)
    return sorted(
        a.path.name for a in Catalogs(catalog).assets(archives, release(version))
    )


def test_attaches_the_zips_of_unchanged_components_too(repo, tmp_path):
    catalog = tmp_path / "catalog"
    publish(repo, catalog, "1.0.0")
    write(repo / "extension.yml", "extension: {id: x, version: 1.1.0}\n")
    publish(repo, catalog, "1.1.0", published=("1.0.0",))

    assert assets(repo, catalog, "1.1.0") == ["p-1.0.0.zip", "x-1.1.0.zip"]


def test_fails_when_a_zip_listed_for_the_release_has_another_sha256(repo, tmp_path):
    catalog = tmp_path / "catalog"
    publish(repo, catalog, "1.0.0")
    write(repo / "commands" / "a.md", "changed after the release pull request")

    with pytest.raises(CheckFailed, match="x-1.0.0.zip: its sha256 is not the one"):
        assets(repo, catalog, "1.0.0")


def test_fails_when_an_unchanged_component_no_longer_builds_the_same_zip(
    repo, tmp_path
):
    catalog = tmp_path / "catalog"
    publish(repo, catalog, "1.0.0")
    write(repo / "extension.yml", "extension: {id: x, version: 1.1.0}\n")
    publish(repo, catalog, "1.1.0", published=("1.0.0",))
    write(repo / "presets" / "p" / "a.md", "changed without a new version")

    with pytest.raises(CheckFailed, match="p-1.0.0.zip: its sha256 is not the one"):
        assets(repo, catalog, "1.1.0")


def test_fails_when_a_version_has_no_record(repo, tmp_path):
    catalog = tmp_path / "catalog"
    publish(repo, catalog, "1.0.0")
    write(repo / "extension.yml", "extension: {id: x, version: 1.1.0}\n")

    with pytest.raises(CheckFailed, match="x-1.1.0.zip: catalog/ has no record"):
        assets(repo, catalog, "1.0.0")


def test_fails_when_the_catalogs_were_not_generated_for_the_release(repo, tmp_path):
    catalog = tmp_path / "catalog"
    publish(repo, catalog, "1.0.0")

    with pytest.raises(
        CheckFailed, match="no current version in catalog/ points to https://r/1.1.0/"
    ):
        assets(repo, catalog, "1.1.0")


def test_fails_for_an_earlier_release_on_a_later_commit(repo, tmp_path):
    catalog = tmp_path / "catalog"
    publish(repo, catalog, "1.0.0")
    write(repo / "extension.yml", "extension: {id: x, version: 1.1.0}\n")
    write(repo / "presets" / "p" / "preset.yml", "preset: {id: p, version: 1.1.0}\n")
    publish(repo, catalog, "1.1.0", published=("1.0.0",))

    with pytest.raises(CheckFailed, match="no current version in catalog/ points to"):
        assets(repo, catalog, "1.0.0")
