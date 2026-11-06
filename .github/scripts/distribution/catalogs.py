"""The catalogs that list the repo's release zips, one file per kind of component."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from distribution.archives import Archive
from repo.components import Component

REPOSITORY = "https://github.com/opsmill/opsmill-speckit"
# Projects read the catalogs from main, so that they list each new release.
CATALOGS = "https://raw.githubusercontent.com/opsmill/opsmill-speckit/main/catalog/"
# The name of these catalogs in a project, which bundles set as `source`.
SOURCE = "opsmill"


@dataclass(frozen=True)
class Location:
    """The URLs that a set of catalogs and zips is served from."""

    catalogs: str
    archives: str

    @classmethod
    def release(cls, version: str) -> "Location":
        """Where a GitHub Release of this repo serves its zips."""
        return cls(CATALOGS, f"{REPOSITORY}/releases/download/v{version}/")


@dataclass(frozen=True)
class Record:
    """The catalog record of one version of a component."""

    # Fields that a historical release keeps, since spec-kit does not inherit them.
    RELEASE_FIELDS: ClassVar[tuple[str, ...]] = (
        "download_url",
        "url",
        "sha256",
        "requires",
        "provides",
    )

    component: Component
    archive: Archive
    location: Location

    def content(self) -> dict:
        """The entry of this version: manifest fields, zip URL and sha256, requirements, counts."""
        info = self.component.info()
        manifest = self.component.content()
        record = {
            key: str(info[key])
            for key in ("id", "name", "version", "role", "description", "author")
            if key in info
        }
        record["repository"] = str(info.get("repository", REPOSITORY))
        if "license" in info:
            record["license"] = str(info["license"])
        record[self.component.url_field] = (
            self.location.archives + self.archive.path.name
        )
        record["sha256"] = self.archive.sha256()
        requires = self.component.requirements()
        if requires:
            record["requires"] = requires
        counts = self.component.counts()
        if counts:
            record["provides"] = counts
        if manifest.get("tags"):
            record["tags"] = [str(tag) for tag in manifest["tags"]]
        return record


@dataclass(frozen=True)
class CatalogFile:
    """The catalog of one kind of component."""

    NAMES: ClassVar[dict[str, str]] = {
        "extensions": "extension-catalog.json",
        "presets": "preset-catalog.json",
        "workflows": "workflow-catalog.json",
        "bundles": "bundle-catalog.json",
    }

    folder: Path
    kind: str

    @property
    def path(self) -> Path:
        return self.folder / self.NAMES[self.kind]

    def content(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def entries(self) -> dict:
        return self.content().get(self.kind) or {}

    def write(self, entries: dict, location: Location) -> None:
        """Write the entries, dated now unless they are the ones already there."""
        old = self.content()
        updated = old.get("updated_at") if entries == self.entries() else None
        content = {
            "schema_version": "1.0",
            "updated_at": updated or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "catalog_url": location.catalogs + self.path.name,
            self.kind: dict(sorted(entries.items())),
        }
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(content, indent=2) + "\n")


@dataclass(frozen=True)
class Catalogs:
    """A folder of catalogs, one per kind of component.

    Entries for components that the repo does not ship are written by hand and
    kept as they are.
    """

    folder: Path

    def publish(
        self,
        archives: dict[Component, Archive],
        location: Location,
        published: tuple[str, ...] = (),
        history: bool = True,
    ) -> None:
        """List the zips as the current releases of their components.

        `published` holds the archive URLs of the releases already published.
        With history, a version whose zip one of them holds keeps its record,
        and a new version moves that record to `releases`. A record of a
        release not published yet is replaced, whether it is this release or a
        release prepared under another number. Without history, each component
        lists only these zips.
        """
        for kind in CatalogFile.NAMES:
            catalog = CatalogFile(self.folder, kind)
            entries = catalog.entries()
            for component, archive in archives.items():
                if component.kind != kind:
                    continue
                record = Record(component, archive, location).content()
                current = entries.get(component.id)
                entries[component.id] = (
                    self.next(current, record, published)
                    if history and current
                    else record
                )
            catalog.write(entries, location)

    def next(self, current: dict, record: dict, published: tuple[str, ...]) -> dict:
        """The entry that replaces `current`, by the rules of `publish`."""
        releases = dict(current.get("releases") or {})
        url = current.get("download_url") or current.get("url") or ""
        if str(url).startswith(published):
            if current["version"] == record["version"]:
                return current
            releases[current["version"]] = {
                key: current[key] for key in Record.RELEASE_FIELDS if key in current
            }
        return {**record, "releases": releases} if releases else record
