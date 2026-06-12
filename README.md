# opsmill-speckit

OpsMill house [spec-kit](https://github.com/github/spec-kit) repo. Ships two
independently installable artifacts:

1. **Extension `opsmill`** — three workflow commands under the `opsmill`
   namespace:
   - `/speckit.opsmill.extract` — extract durable knowledge, guidelines, and
     ADRs from completed spec directories into `dev/knowledge/`,
     `dev/guidelines/`, `dev/adr/`.
   - `/speckit.opsmill.retrospect` — run a session retrospective that surfaces
     context-management gaps and routes them to `fix-now`, `open-pr`,
     `github-issue`, or `local-only` dispositions.
   - `/speckit.opsmill.summary` — produce a flow-level timeline of the current
     Claude Code session next to `spec.md` / `plan.md` in the active feature
     directory.

2. **Presets** — drop-in overrides for spec-kit commands (native or
   extension-provided). Each preset is installed independently of the
   extension. Currently two ship:
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
     `dev/guidelines/` + `dev/adr/`, and the report is Jira- and
     extraction-aware. Requires the `reconcile` extension to be
     installed in the consumer repo.

## Requires

- spec-kit `>=0.8.0`
- `check-prerequisites.sh` (shipped by spec-kit core; present at
  `.specify/scripts/bash/check-prerequisites.sh` in any spec-kit-initialized
  repo). Used by the `summary` command via the `{SCRIPT}` placeholder.

## Install

Latest `main`:

```bash
specify extension add opsmill \
  --from https://github.com/opsmill/opsmill-speckit/archive/refs/heads/main.zip
```

Pinned release:

```bash
specify extension add opsmill \
  --from https://github.com/opsmill/opsmill-speckit/archive/refs/tags/v1.0.0.zip
```

Local development install (from a working tree):

```bash
specify extension add --dev /path/to/opsmill-speckit
```

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

### `/speckit.taskstoissues` (preset override)

Provided by the [`taskstoissues-jira`](presets/taskstoissues-jira/README.md)
preset, not the extension. Install separately:

```bash
specify preset add taskstoissues-jira \
  --from https://github.com/opsmill/opsmill-speckit/archive/refs/heads/main.zip \
  --subdir presets/taskstoissues-jira
```

See [`presets/taskstoissues-jira/README.md`](presets/taskstoissues-jira/README.md)
for config (`dev/jira.yml`) and failure-mode details.

### `/speckit.reconcile.run` (preset override)

Provided by the [`reconcile-opsmill`](presets/reconcile-opsmill/README.md)
preset, not the extension. Overrides the command of the
[stn1slv/spec-kit-reconcile](https://github.com/stn1slv/spec-kit-reconcile)
extension, which must already be installed in the consumer repo:

```bash
specify extension add reconcile \
  --from https://github.com/stn1slv/spec-kit-reconcile/archive/refs/heads/main.zip

git clone https://github.com/opsmill/opsmill-speckit
specify preset add --dev opsmill-speckit/presets/reconcile-opsmill
```

See [`presets/reconcile-opsmill/README.md`](presets/reconcile-opsmill/README.md)
for provenance and behavior.

## Hooks (auto-fire during SDD)

The extension registers two opt-in hooks at install time. Each prompts before
running (`optional: true`):

| Event | Command | Purpose |
|---|---|---|
| `after_implement` | `/speckit.opsmill.extract` | Promote durable knowledge / guidelines / ADRs out of the just-completed spec. |
| `after_taskstoissues` | `/speckit.opsmill.summary` | Capture the session timeline at the moment of handoff to the issue tracker. |

`/speckit.opsmill.retrospect` is not wired by default — it remains a manual
command for interactive session reflection.

The `extension.yml` `hooks:` schema accepts one command per event. To fire
additional commands at the same event, append entries to your repo's
`.specify/extensions.yml` registry. Example: also fire `summary` at
`after_implement`:

```yaml
# .specify/extensions.yml (consumer-side, snippet)
hooks:
  after_implement:
    - extension: opsmill
      command: speckit.opsmill.summary
      enabled: true
      optional: true
      prompt: "Produce a session summary in the feature directory?"
```

## Provenance

Command bodies in v1 are verbatim lifts from
`opsmill/styrmin/.specify/extensions/`:

- `commands/extract.md` ← `extract/commands/extract.md`
- `commands/retrospect.md` ← `retrospect/commands/retrospect.md`
- `commands/summary.md` ← `summary/commands/run.md`

Two surgical line edits update self-references to the namespaced form
(`speckit.opsmill.<cmd>`); no other content changes. See `CHANGELOG.md`
for the exact lines.

## License

Apache-2.0. See `LICENSE`.
