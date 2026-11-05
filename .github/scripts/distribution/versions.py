"""Rules that keep component versions, bundle pins and catalogs in step."""

import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from packaging.version import Version

from distribution.archives import build
from distribution.catalogs import SOURCE, CatalogFile
from install_check.errors import CheckFailed
from repo.components import Components


def fail_on(errors: list[str]) -> None:
    if errors:
        raise CheckFailed("\n".join(errors))


def zips(repo: Path, dest: Path) -> dict[tuple[str, str], tuple[str, str]]:
    """The version and zip sha256 of each component, by kind and ID."""
    return {
        (component.kind, component.id): (component.version, archive.sha256())
        for component, archive in build(Components(repo), dest).items()
    }


@contextmanager
def worktree(repo: Path, revision: str, dest: Path) -> Iterator[Path]:
    git = ["git", "-C", str(repo), "worktree"]
    subprocess.run([*git, "add", "-q", "--detach", str(dest), revision], check=True)
    try:
        yield dest
    finally:
        subprocess.run([*git, "remove", "--force", str(dest)], check=True)


@dataclass(frozen=True)
class VersionRaised:
    """A component or bundle whose zip changed since a base revision has a higher version.

    spec-kit compares versions, so a change shipped under the same version
    never reaches a project that installed that version. A bundle's zip holds
    its pins, so a new pin changes it.
    """

    repo: Path
    base: str

    def verify(self) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            with worktree(self.repo, self.base, Path(tmp) / "base") as base:
                old = zips(base, Path(tmp) / "old")
            new = zips(self.repo, Path(tmp) / "new")
        changed = [key for key in new if key in old and old[key][1] != new[key][1]]
        fail_on(
            [
                f"{key[1]} changed since {self.base}: raise its version above {old[key][0]}"
                for key in changed
                if Version(new[key][0]) <= Version(old[key][0])
            ]
        )
        return f"{len(changed)} changed components and bundles have a higher version"


@dataclass(frozen=True)
class PinsMatch:
    """Bundles pin the repo's current versions, and listed third-party versions.

    Every extension and preset of the repo is in a bundle, since repos install
    them only through bundles.
    """

    repo: Path

    def verify(self) -> str:
        components = Components(self.repo)
        versions = {(c.kind, c.id): c.version for c in components}
        errors, pinned = [], set()
        for bundle in components.bundles():
            for kind, ref in bundle.references():
                key, version = (kind, str(ref["id"])), str(ref["version"])
                pin = f"{bundle.id} pins {key[1]} {version}"
                if key in versions:
                    pinned.add(key)
                    if version != versions[key]:
                        errors.append(f"{pin}, its manifest has {versions[key]}")
                    if ref.get("source") != SOURCE:
                        errors.append(f"{pin} without source: {SOURCE}")
                # Spec Kit resolves a pin from another catalog, or without a
                # source, itself.
                elif ref.get("source") == SOURCE and version not in self.listed(
                    kind, key[1]
                ):
                    errors.append(f"{pin}, which catalog/ does not list")
        errors += [
            f"{component_id} is in no bundle"
            for kind, component_id in versions
            if kind != "bundles" and (kind, component_id) not in pinned
        ]
        fail_on(errors)
        return f"bundles pin {len(pinned)} components and bundles at their versions"

    def listed(self, kind: str, component_id: str) -> set[str]:
        entry = CatalogFile(self.repo / "catalog", kind).entries().get(component_id)
        if not entry:
            return set()
        return {str(entry["version"]), *(entry.get("releases") or {})}


@dataclass(frozen=True)
class CatalogMatches:
    """A version that catalog/ lists for a component of the repo has the zip built now."""

    repo: Path

    def verify(self) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            built = zips(self.repo, Path(tmp))
        errors, listed = [], 0
        for (kind, component_id), (version, sha) in built.items():
            entry = CatalogFile(self.repo / "catalog", kind).entries().get(component_id)
            if not entry:
                continue
            records = {str(entry["version"]): entry, **(entry.get("releases") or {})}
            if version not in records:
                continue
            listed += 1
            if records[version].get("sha256") != sha:
                errors.append(
                    f"catalog/ lists {component_id} {version} with another zip: raise its version, "
                    "or run build_release.py catalog for the release that is not published yet"
                )
        fail_on(errors)
        return f"{listed} versions listed in catalog/ match their zips"
