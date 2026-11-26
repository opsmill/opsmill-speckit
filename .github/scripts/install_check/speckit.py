"""The Spec Kit versions that a repo's components accept."""

from dataclasses import dataclass

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from install_check.errors import CheckFailed
from repo.components import Component, Components


@dataclass(frozen=True)
class SpeckitFloor:
    """The oldest spec-kit version that every manifest accepts."""

    components: Components

    def version(self) -> Version:
        bounds = [
            bound for component in self.components for bound in self.bounds(component)
        ]
        if not bounds:
            raise CheckFailed("no manifest declares requires.speckit_version")
        return max(bounds)

    def bounds(self, component: Component) -> list[Version]:
        spec = (component.content().get("requires") or {}).get("speckit_version")
        if not spec:
            return []
        lower = [Version(s.version) for s in SpecifierSet(spec) if s.operator == ">="]
        if not lower:
            manifest = component.manifest.relative_to(component.root)
            raise CheckFailed(
                f"{manifest}: speckit_version {spec!r} has no inclusive lower bound; use >="
            )
        return lower

    def tag(self) -> str:
        """The version as a spec-kit release tag, X.Y.Z."""
        return ".".join(str(part) for part in (*self.version().release, 0, 0)[:3])
