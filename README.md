# opsmill-speckit

OpsMill house [spec-kit](https://github.com/github/spec-kit) repo. It holds:

1. **Extension `opsmill`** — seven workflow commands under the `opsmill`
   namespace:
   - `/speckit.opsmill.auto` — run the full pipeline end-to-end (prep +
     implement) autonomously, making all decisions without pausing. Stops
     before extract.
   - `/speckit.opsmill.prep` — run the preparation phases
     (specify → plan → critique → tasks → spec/ask alignment check)
     autonomously, stopping before implementation.
   - `/speckit.opsmill.implement` — run the implementation + review tail from an
     existing `tasks.md` in clean-context subagents, then emit a final report.
   - `/speckit.opsmill.extract` — extract durable knowledge, guidelines, and
     ADRs from completed spec directories into `dev/knowledge/`,
     `dev/guidelines/`, `dev/adr/`.
   - `/speckit.opsmill.retrospect` — run a session retrospective that surfaces
     context-management gaps and routes them to `fix-now`, `open-pr`,
     `github-issue`, or `local-only` dispositions.
   - `/speckit.opsmill.summary` — produce a flow-level timeline of the current
     Claude Code session next to `spec.md` / `plan.md` in the active feature
     directory.
   - `/speckit.opsmill.qa` — produce a manual QA checklist (`qa-checklist.md`)
     next to `spec.md` / `plan.md` so a human tester can verify the
     just-implemented feature step-by-step.

2. **Presets** — drop-in overrides for spec-kit commands (native or
   extension-provided). Four ship:
   - [`taskstoissues-jira`](presets/taskstoissues-jira/README.md) — overrides
     `/speckit.taskstoissues` with a Jira-flavored implementation that fans
     `tasks.md` out into Jira issues under a single Epic (one issue per
     `## Phase N:` block) via the Atlassian MCP.
   - [`reconcile-opsmill`](presets/reconcile-opsmill/README.md) — overrides
     `/speckit.reconcile.run` from the
     [stn1slv/spec-kit-reconcile](https://github.com/stn1slv/spec-kit-reconcile)
     extension with an OpsMill-adapted command body: remediation tasks
     stay inside `## Phase <N>:` blocks, `[P]` keeps its core
     "parallelizable" meaning, the compliance gate reads
     `dev/guidelines/` + `dev/adr/`, and the report is
     Jira-aware.
   - [`critique-opsmill`](presets/critique-opsmill/README.md) — overrides
     `/speckit.critique.run`, whose upstream version looks for its script in
     the wrong folder. Requires the `critique` extension.
   - [`jira-branch`](presets/jira-branch/README.md) — overrides
     `/speckit.git.feature` so that a feature branch needs a JPD or Jira
     reference. Requires the git extension.

## Bundles

Repos install opsmill-speckit only through one of its two bundles, which pin
every component at an exact version:

| Bundle | For | Installs |
|---|---|---|
| [`opsmill-sdd`](bundles/opsmill-sdd/README.md) | every repo | `opsmill`, `checkpoint`, `critique` with `critique-opsmill`, `reconcile` with `reconcile-opsmill` |
| [`opsmill-jira`](bundles/opsmill-jira/README.md) | repos that track their work in Jira | everything in `opsmill-sdd`, plus `jira-branch`, `taskstoissues-jira` and the `git` extension |

`checkpoint`, `critique` and `reconcile` are third-party extensions, pinned in
the [opsmill catalogs](catalog/README.md). [`CHANGELOG.md`](CHANGELOG.md)
lists the version of every bundle and component in each release.

## Requires

- Spec Kit 1.2.4 or later. CI installs both bundles on that version for each
  pull request, and on the latest Spec Kit every week.
- `check-prerequisites.sh` (shipped by spec-kit core; present at
  `.specify/scripts/bash/check-prerequisites.sh` in any spec-kit-initialized
  repo). Used by the `summary` command via the `{SCRIPT}` placeholder.
- PyYAML for the Python that spec-kit's scripts run: `python3`, or the one set
  in `SPECKIT_PYTHON_EXECUTABLE`. spec-kit needs it to read the presets'
  manifests; without it, `/speckit.plan` cannot prepare `plan.md`.

Recommended: the `pr-review-toolkit` Claude Code plugin, which gives
`implement` its full review pass (see [Review plugin](#review-plugin)).

## Install

### 1. Declare the opsmill catalogs, once per repo

A bundle cannot add the catalogs that its components come from: Spec Kit
looks them up in the catalogs that the project declares
([Spec Kit bundles reference](https://github.com/github/spec-kit/blob/v1.2.4/docs/reference/bundles.md#publish-a-bundle)).
Run `specify init` first if the repo has no `.specify/` folder. Then copy the
three files of [`catalog/specify/`](catalog/specify/) into `.specify/` and
commit them:

```bash
for kind in extension preset bundle; do
  curl -fsSL -o ".specify/$kind-catalogs.yml" \
    "https://raw.githubusercontent.com/opsmill/opsmill-speckit/main/catalog/specify/$kind-catalogs.yml"
done
```

- A project's extension or preset catalog file replaces Spec Kit's built-in
  catalogs, so these files list Spec Kit's `default` and `community` catalogs
  again after the opsmill one
  ([Spec Kit catalogs reference](https://github.com/github/spec-kit/blob/v1.2.4/docs/reference/catalogs.md#inspect-and-manage-catalog-sources)).
  The bundle catalog file adds to the built-in bundle catalogs.
- The command replaces these files if the repo already has them. When the repo
  declares other catalogs, copy the `opsmill` entry of each file into the
  repo's file instead.
- A developer can instead copy the same files into `~/.specify/`, once per
  machine.
- Do not use the `SPECKIT_*_CATALOG_URL` environment variables: they replace
  every catalog, including Spec Kit's own.

`specify extension catalog list`, `specify preset catalog list` and
`specify bundle catalog list` show the catalogs that the project uses.

### 2. Install one bundle

```bash
specify bundle install opsmill-sdd    # every repo
specify bundle install opsmill-jira   # repos that use Jira, instead of opsmill-sdd
```

`opsmill-jira` includes `opsmill-sdd`, so a repo installs only one of them.
`specify bundle list`, `specify extension list` and `specify preset list`
show what is installed.

To move to the versions of a later release, run
`specify bundle update <bundle-id>`. A bundle does not remove components that
it never installed.

### Local development

From a working tree, install a component without the catalogs:

```bash
specify extension add --dev /path/to/opsmill-speckit
specify preset add --dev /path/to/opsmill-speckit/presets/<preset-id>
```

### Review plugin

[`pr-review-toolkit`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/pr-review-toolkit)
is a Claude Code plugin whose review agents `implement` runs: five in
parallel, then `code-simplifier` alone, whose edits become findings and are
discarded. Without it, `implement` uses `/code-review` if available. In Claude
Code:

```text
/plugin install pr-review-toolkit@claude-plugins-official
```

When the critique or review provider is missing, `prep`, `auto`, and
`implement` fall back to a reduced built-in critique or review subagent. The
fallback is always reported on the machine-readable status line (`CRITIQUE:` /
`REVIEW:`) and in the run summary, so a degraded run is never silent.

## Upgrading spec-kit to 1.2 or later

From `v1.4.0`, the workflow runs on spec-kit 1.2 and later. In a repo that
uses an older spec-kit:

1. Remove the `review` extension, which does not install on spec-kit 1.x:
   `specify extension remove review`.
2. Upgrade the CLI:
   `uv tool install specify-cli --force --from git+https://github.com/github/spec-kit.git@v1.2.3`,
   then `specify integration upgrade claude`.
3. Reinstall `opsmill` from the `v1.4.0` tag (see [Install](#install)):
   `specify extension remove opsmill`, then `specify extension add opsmill --from …`.
4. Install the [companions](#companion-extensions) that the repo does not have
   yet (`specify extension list` shows them): `checkpoint`, `critique`, and the
   `pr-review-toolkit` plugin. Then add the `critique-opsmill` preset, also
   when `critique` was already installed.
5. If the repo has the
   [`infrahub` preset](https://github.com/opsmill/infrahub/tree/4d9fd0f0a469217aada697cb5ef306f7ef485f78/dev/spec-kit/presets/infrahub)
   copied from opsmill/infrahub, which checks branch names against Jira,
   replace it with [`jira-branch`](presets/jira-branch/README.md).
6. Each developer makes PyYAML available to the Python that spec-kit's scripts
   run (see [Requires](#requires)).

## Commands

### `/speckit.opsmill.extract`

Analyzes one or more completed spec directories and extracts durable knowledge
into the project's documentation system (`dev/knowledge/`, `dev/guidelines/`,
`dev/adr/`), then marks each spec as extracted.

Accepts multiple specs as space-separated arguments and processes them
sequentially.

### `/speckit.opsmill.retrospect`

Runs a retrospective on the current agent session while the work is still
fresh in context. Identifies concrete improvements to the repository's
context-management surface area (`AGENTS.md`, `CLAUDE.md`,
`.claude/settings.json`, `.agents/skills/`, `.agents/commands/`,
`.specify/templates/`, `dev/knowledge/`, `dev/guides/`, `dev/guidelines/`,
`dev/adr/`) and routes them through user-approved dispositions.

Stays read-only until the user approves each disposition bucket.

### `/speckit.opsmill.summary`

Produces a flow-level summary of the current Claude Code session — executive
summary, chronological timeline, and outcomes — written into the active
feature directory next to `spec.md` / `plan.md`.

Supports `--since <commit|time>` to bound the summary window.

### `/speckit.opsmill.qa`

Produces a manual QA checklist at `FEATURE_DIR/qa-checklist.md` that walks
a human tester through verifying the just-implemented feature. Scope is
**manual / user-facing only** — exact commands, URLs, UI paths, and the
outputs to look for. Automated test suites are intentionally out of scope.

The checklist is organized into Scope, Prerequisites, Setup, Test Scenarios,
Edge Cases, Teardown, and Sign-off sections. Re-running on the same feature
prompts before overwriting; pass `--force` to skip the prompt, or any other
free-form text as scope guidance (e.g. `focus on the CLI surface`).

### `/speckit.taskstoissues` (preset override)

Provided by the [`taskstoissues-jira`](presets/taskstoissues-jira/README.md)
preset, not the extension. See [`presets/taskstoissues-jira/README.md`](presets/taskstoissues-jira/README.md)
for config (`dev/jira.yml`) and failure-mode details.

### `/speckit.reconcile.run` (preset override)

The `/speckit.reconcile.run` command comes from the
[stn1slv/spec-kit-reconcile](https://github.com/stn1slv/spec-kit-reconcile)
extension; the [`reconcile-opsmill`](presets/reconcile-opsmill/README.md)
preset overrides its body. See [`presets/reconcile-opsmill/README.md`](presets/reconcile-opsmill/README.md)
for provenance and behavior.

### `/speckit.critique.run` and `/speckit.git.feature` (preset overrides)

See [`critique-opsmill`](presets/critique-opsmill/README.md) and
[`jira-branch`](presets/jira-branch/README.md) for what they change.

## Hooks (auto-fire during SDD)

The extension registers one opt-in hook at install time. It prompts before
running (`optional: true`):

| Event | Command | Purpose |
|---|---|---|
| `after_taskstoissues` | `/speckit.opsmill.summary` | Capture the session timeline at the moment of handoff to the issue tracker. |

`/speckit.opsmill.extract`, `/speckit.opsmill.retrospect`, and
`/speckit.opsmill.qa` are not wired by default — they remain manual commands.
Extract is intentionally manual so the user can review the implementation
report before promoting content into `dev/`.

The `extension.yml` `hooks:` schema accepts one command per event. To fire
additional commands at the same event (or to re-wire `extract` or `qa` to
fire automatically after implement if you prefer that workflow), append
entries to your repo's `.specify/extensions.yml` registry. Example: fire
`extract` and `qa` at `after_implement` on the consumer side:

```yaml
# .specify/extensions.yml (consumer-side, snippet)
hooks:
  after_implement:
    - extension: opsmill
      command: speckit.opsmill.extract
      enabled: true
      optional: true
      prompt: "Extract knowledge, guidelines, and ADRs from the completed spec?"
    - extension: opsmill
      command: speckit.opsmill.qa
      enabled: true
      optional: true
      prompt: "Create QA testing checklist?"
```

## Troubleshooting

### `implement` or `auto` reports `REVIEW: none` / `CRITIQUE: none`

No critique or review provider was available **and** the harness offered no
subagent dispatch, so no fallback was possible. `REVIEW: none` marks the run
`INCOMPLETE` by design. Install the missing bundle or the
[review plugin](#review-plugin), and re-run the gate over the same diff.

## Provenance

The `extract`, `retrospect`, and `summary` command bodies originated as lifts
from an internal spec-kit extensions set, with two surgical line edits to
update self-references to the namespaced form (`speckit.opsmill.<cmd>`); no
other content changes.

The `auto`, `prep`, and `implement` commands (added in 1.1.0) are authored
from scratch in this repo — they are **not** lifts. See `CHANGELOG.md`.

## License

Apache-2.0. See `LICENSE`.
