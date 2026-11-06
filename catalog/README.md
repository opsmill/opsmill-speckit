# Catalogs

The Spec Kit catalogs that list the OpsMill bundles and every component they
install. A project reads them from `main`, through the files in
[`specify/`](specify/), which it copies into its `.specify/` folder.

- `extension-catalog.json`: the `opsmill` extension, and the third-party
  extensions that the bundles pin (`checkpoint`, `critique`, `reconcile`)
- `preset-catalog.json`: the presets in [`presets/`](../presets/)
- `workflow-catalog.json`: the Spec Kit workflows in [`workflows/`](../workflows/)
- `bundle-catalog.json`: the bundles in [`bundles/`](../bundles/)

Each entry gives the URL and `sha256` of a zip: in `download_url`, or in `url`
for a workflow. Older versions stay
listed under `releases`, as described in the
[Spec Kit catalog reference](https://github.com/github/spec-kit/blob/v1.2.4/docs/reference/catalogs.md)
and [bundle reference](https://github.com/github/spec-kit/blob/v1.2.4/docs/reference/bundles.md#catalog-release-history).

## Update for a release

The entries of OpsMill components and bundles are generated from their
manifests. In the pull request that prepares release `X.Y.Z`, commit the new
versions of the manifests and the bundle pins first, since the command refuses
a working tree with changes. Then fetch the tags, run the command, and commit
`catalog/`:

```bash
git fetch --tags
uv run .github/scripts/build_release.py catalog X.Y.Z
```

A version that is new gets a `download_url` in the GitHub Release `vX.Y.Z`.
A version from a published release, whose tag exists, keeps its record. A
record of a release that has no tag yet is replaced, so the release pull
request can still change its release number. The zips are the same
bytes for the same files, so the release of that commit publishes zips with
the recorded `sha256`.

The third-party entries are written by hand: copy the `download_url` of the
upstream tag archive and the `sha256` of that archive, and pin the same version
in the bundles.

## Publish a release

In the release pull request, also replace `Unreleased` with the release date in
the `CHANGELOG.md` entry. After the release pull request is merged, publish the
GitHub Release `vX.Y.Z` on `main`, with the release's `CHANGELOG.md` entry as
notes.

The [Release workflow](../.github/workflows/release.yml) then runs on the
tagged commit:

1. It builds the zips with
   `uv run .github/scripts/build_release.py assets X.Y.Z DIR`.
2. It checks that each zip whose URL in `catalog/` points to `vX.Y.Z` has the
   recorded `sha256`.
3. It attaches those zips to the release.

If a zip is missing or has another `sha256`, the workflow fails and attaches
nothing, since Spec Kit would refuse to install that zip. This happens when a
pull request merged after the release pull request changed a component.
`build_release.py` also refuses a working tree with changes or untracked files,
whose zips no commit can rebuild.
