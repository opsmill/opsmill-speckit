import json
import subprocess

import pytest
from support import write

from distribution.archives import build
from distribution.catalogs import Catalogs, Location
from repo.components import Components


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    write(root / "extension.yml", "extension: {id: x, version: 1.0.0}\n")
    return root


def publish(repo, release: str, published: tuple[str, ...] = ()) -> dict:
    """List the repo's zips as release `release`, and return the extension entries."""
    catalog = repo.parent / "catalog"
    archives = build(Components(repo), repo.parent / "dist" / release)
    location = Location("https://c/", f"https://r/{release}/")
    published_urls = tuple(f"https://r/{version}/" for version in published)
    Catalogs(catalog).publish(archives, location, published_urls)
    return json.loads((catalog / "extension-catalog.json").read_text())["extensions"]


class TestCatalogs:
    def test_keeps_earlier_releases_and_entries_written_by_hand(self, repo):
        write(
            repo.parent / "catalog" / "extension-catalog.json",
            json.dumps({"extensions": {"other": {"id": "other", "version": "3.0.0"}}}),
        )
        first = publish(repo, "1.0.0")["x"]
        write(repo / "extension.yml", "extension: {id: x, version: 1.1.0}\n")

        entries = publish(repo, "1.1.0", published=("1.0.0",))

        assert entries["other"] == {"id": "other", "version": "3.0.0"}
        assert entries["x"]["download_url"] == "https://r/1.1.0/x-1.1.0.zip"
        assert entries["x"]["releases"]["1.0.0"]["sha256"] == first["sha256"]

    def test_a_published_version_keeps_its_record(self, repo):
        first = publish(repo, "1.0.0")["x"]
        write(repo / "commands" / "a.md", "changed without a new version")

        assert publish(repo, "1.1.0", published=("1.0.0",))["x"] == first

    def test_a_version_of_the_release_being_prepared_is_rebuilt(self, repo):
        first = publish(repo, "1.0.0")["x"]
        write(repo / "extension.yml", "extension: {id: x, version: 1.0.0}\nname: y\n")

        entry = publish(repo, "1.0.0")["x"]

        assert entry["sha256"] != first["sha256"]
        assert "releases" not in entry

    def test_a_release_renumbered_before_it_is_published_moves_its_records(self, repo):
        publish(repo, "2.1.0")

        entry = publish(repo, "2.2.0")["x"]

        assert entry["download_url"] == "https://r/2.2.0/x-1.0.0.zip"
        assert "releases" not in entry
