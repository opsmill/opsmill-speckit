"""The repo's catalogs and zips, served on localhost as a release serves them."""

import functools
import os
import shutil
import ssl
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from distribution.archives import build
from distribution.catalogs import CATALOGS, Catalogs, Location
from install_check.errors import CheckFailed
from install_check.project import Project
from repo.components import Components


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass


@dataclass(frozen=True)
class LocalRelease:
    """The zips of the working tree, listed in a copy of the repo's catalogs.

    Spec Kit 1.4.0 and later refuse a catalog URL that does not use HTTPS, on
    localhost too. The release is served over HTTPS with a certificate made for
    the run, which SSL_CERT_FILE makes the specify commands of the run trust.
    """

    repo: Path
    folder: Path

    @contextmanager
    def serve(self) -> Iterator[Location]:
        self.folder.mkdir(parents=True, exist_ok=True)
        tls = Certificate(self.folder.parent / "tls").create()
        handler = functools.partial(QuietHandler, directory=str(self.folder))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(tls.cert, tls.key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        previous = os.environ.get("SSL_CERT_FILE")
        os.environ["SSL_CERT_FILE"] = str(tls.trusted)
        try:
            url = f"https://127.0.0.1:{server.server_address[1]}/"
            location = Location(url, url)
            for catalog in (self.repo / "catalog").glob("*.json"):
                shutil.copy2(catalog, self.folder / catalog.name)
            archives = build(Components(self.repo), self.folder)
            # Without history: a version that the working tree changes is not
            # published yet, and its record must list the zip built here.
            Catalogs(self.folder).publish(archives, location, history=False)
            yield location
        finally:
            if previous is None:
                os.environ.pop("SSL_CERT_FILE", None)
            else:
                os.environ["SSL_CERT_FILE"] = previous
            server.shutdown()
            server.server_close()


@dataclass(frozen=True)
class Certificate:
    """A self-signed certificate for 127.0.0.1, valid for one day."""

    folder: Path

    @property
    def cert(self) -> Path:
        return self.folder / "cert.pem"

    @property
    def key(self) -> Path:
        return self.folder / "key.pem"

    @property
    def trusted(self) -> Path:
        """The system's certificate authorities, plus this certificate.

        Keeping the system's ones lets the specify commands of the run still
        reach other HTTPS hosts.
        """
        return self.folder / "trusted.pem"

    def create(self) -> "Certificate":
        self.folder.mkdir(parents=True, exist_ok=True)
        # The openssl of the GitHub runners and of macOS both accept -addext.
        result = subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-days", "1", "-subj", "/CN=127.0.0.1",
                "-addext", "subjectAltName=IP:127.0.0.1",
                "-keyout", str(self.key), "-out", str(self.cert),
            ],
            check=False,
            capture_output=True,
            text=True,
        )  # fmt: skip
        if result.returncode != 0:
            raise CheckFailed(
                f"openssl could not create a certificate:\n{result.stderr}"
            )
        defaults = ssl.get_default_verify_paths()
        system = next(
            (
                Path(name)
                for name in (defaults.cafile, defaults.openssl_cafile)
                if name and Path(name).is_file()
            ),
            None,
        )
        authorities = system.read_text() if system else ""
        self.trusted.write_text(authorities + self.cert.read_text())
        return self


@dataclass(frozen=True)
class Declaration:
    """The catalog files that a project commits in .specify/, as the README shows."""

    repo: Path

    def write(self, project: Project, location: Location) -> None:
        files = sorted((self.repo / "catalog" / "specify").glob("*.yml"))
        if not files:
            raise CheckFailed("catalog/specify/ holds no catalog file to declare")
        for path in files:
            text = path.read_text()
            if CATALOGS not in text:
                raise CheckFailed(
                    f"{path.relative_to(self.repo)} does not declare the catalogs at {CATALOGS}"
                )
            target = project.path / ".specify" / path.name
            target.write_text(text.replace(CATALOGS, location.catalogs))
