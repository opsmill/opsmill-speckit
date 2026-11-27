import json
import os
import subprocess
import sys

import pytest
from support import write

from install_check.catalogs import LocalRelease


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    write(root / "extension.yml", "extension: {id: x, version: 1.0.0}\n")
    return root


def fetch(url: str) -> bytes:
    """Read a URL in a new process, as the specify commands of the check do."""
    code = (
        "import sys, urllib.request; "
        "sys.stdout.buffer.write(urllib.request.urlopen(sys.argv[1]).read())"
    )
    return subprocess.run(
        [sys.executable, "-c", code, url], check=True, capture_output=True
    ).stdout


def test_serves_the_catalogs_and_zips_over_https_to_child_processes(repo, tmp_path):
    with LocalRelease(repo, tmp_path / "release").serve() as location:
        assert location.catalogs.startswith("https://127.0.0.1:")
        catalog = json.loads(fetch(f"{location.catalogs}extension-catalog.json"))
        entry = catalog["extensions"]["x"]
        assert entry["download_url"] == f"{location.archives}x-1.0.0.zip"
        assert fetch(entry["download_url"])[:2] == b"PK"


def test_restores_ssl_cert_file(repo, tmp_path, monkeypatch):
    monkeypatch.setenv("SSL_CERT_FILE", "/elsewhere.pem")
    with LocalRelease(repo, tmp_path / "release").serve():
        assert os.environ["SSL_CERT_FILE"] != "/elsewhere.pem"
    assert os.environ["SSL_CERT_FILE"] == "/elsewhere.pem"
