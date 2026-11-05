"""The repo's catalogs and zips, served on localhost as a release serves them."""

import functools
import shutil
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
    """The zips of the working tree, listed in a copy of the repo's catalogs."""

    repo: Path
    folder: Path

    @contextmanager
    def serve(self) -> Iterator[Location]:
        handler = functools.partial(QuietHandler, directory=str(self.folder))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/"
            location = Location(url, url)
            self.folder.mkdir(parents=True, exist_ok=True)
            for catalog in (self.repo / "catalog").glob("*.json"):
                shutil.copy2(catalog, self.folder / catalog.name)
            archives = build(Components(self.repo), self.folder)
            # Without history: a version that the working tree changes is not
            # published yet, and its record must list the zip built here.
            Catalogs(self.folder).publish(archives, location, history=False)
            yield location
        finally:
            server.shutdown()
            server.server_close()


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
