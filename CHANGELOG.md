# Changelog

All notable changes to opsmill-speckit are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-05-19

### Added
- New `taskstoissues-jira` preset under `presets/taskstoissues-jira/`,
  authored to the spec-kit preset schema (`schema_version: "1.0"`,
  `preset.id: "taskstoissues-jira"`, `requires.speckit_version: ">=0.8.0"`).
  Declares one command override under `provides.templates`:
  `type: command`, `name: speckit.taskstoissues`,
  `file: commands/speckit.taskstoissues.md`,
  `replaces: speckit.taskstoissues` (default `replace` strategy). Installable
  independently of the `opsmill` extension via
  `specify preset add taskstoissues-jira --subdir presets/taskstoissues-jira`.
- Preset contents:
  - `commands/speckit.taskstoissues.md` — one Jira issue per `## Phase N:`
    block in `tasks.md`, with `Blocks` links derived from `T<NNN>` mentions
    (transitively reduced). Talks to Atlassian through the Atlassian MCP.
  - `templates/jira.example.yml` — template the consumer copies to
    `dev/jira.yml` at their repo root. Holds every Jira parameter the
    preset reads: `cloud`, `default_project_key`, `default_issue_type`,
    `custom_fields.{epic_link,team}`, `team.{name,id}`, `labels_default`.
    Since `dev/jira.yml` lives outside the preset install dir, re-running
    `specify preset add taskstoissues-jira` to update the preset never
    clobbers consumer config. The assignee is the user authenticated to
    the Atlassian MCP (resolved via `atlassianUserInfo`) — no per-user
    config file is needed.
  - `README.md` — preset-level install and setup docs.

### Changed
- The `taskstoissues` workflow is now shipped as a **preset override** of
  the native `speckit.taskstoissues` command rather than as an additive
  `speckit.opsmill.taskstoissues` extension command. Earlier draft of this
  unreleased entry took the opposite stance — that decision is reversed
  here: presets are the right vehicle for replacing a core command, and
  matching the native command name keeps the user-facing surface
  (`/speckit.taskstoissues`) consistent across consumer repos regardless of
  whether this preset is installed.
- `extension.yml` no longer declares `speckit.opsmill.taskstoissues` under
  `provides.commands`. The `hooks.after_taskstoissues` entry stays — it
  fires after `speckit.taskstoissues` runs, including when that command is
  served by the new preset.
- Consumer install paths shift from `.specify/extensions/opsmill/` to
  `.specify/presets/taskstoissues-jira/` for the preset's command body
  and template. Project config lives at `dev/jira.yml` at the repo root.

### Provenance
Ported from the Infrahub preset in
[opsmill/infrahub#9208](https://github.com/opsmill/infrahub/pull/9208).
Generalized for cross-repo reuse:
- Project key + Epic key regex driven by `default_project_key` from config
  rather than hardcoded `IFC`.
- Custom field IDs reduced to placeholders (`customfield_XXXXX`); operator
  resolves real IDs via `getJiraIssueTypeMetaWithFields`.
- Preset id renamed from `infrahub` to `taskstoissues-jira` so the install
  path reads as a portable Jira-flavored override of `speckit.taskstoissues`
  rather than a single-product preset.

## [1.0.0] - 2026-05-11

### Added
- Initial release. Single spec-kit extension (`id: opsmill`,
  `schema_version: "1.0"`, `requires.speckit_version: ">=0.8.0"`) providing:
  - `speckit.opsmill.extract` — knowledge / guidelines / ADR extraction
    from completed spec directories.
  - `speckit.opsmill.retrospect` — session retrospective with
    user-approved disposition routing.
  - `speckit.opsmill.summary` — flow-level session summary in the
    active feature directory.
- `requires.scripts: ["check-prerequisites.sh"]` declared (script is shipped
  by spec-kit core; not vendored here).
- Two opt-in hooks declared in `extension.yml` so the commands auto-prompt
  during the SDD flow:
  - `after_implement` → `speckit.opsmill.extract`
  - `after_taskstoissues` → `speckit.opsmill.summary`
  Both `optional: true`; users are prompted before each fires.

### Provenance
Command bodies are lifted from `opsmill/styrmin/.specify/extensions/`:
- `commands/extract.md` from `extract/commands/extract.md`. Single edit:
  line 255 self-reference `speckit.extract` rewritten to
  `speckit.opsmill.extract`.
- `commands/retrospect.md` from `retrospect/commands/retrospect.md`.
  Verbatim, no edits.
- `commands/summary.md` from `summary/commands/run.md` (renamed). Single
  edit: line 62 self-reference `/speckit.summary.run` rewritten to
  `/speckit.opsmill.summary`.

## Smoke test — 2026-05-11T18:05:00Z

- ZIP install: PASS — Created `/tmp/opsmill-speckit-smoke/opsmill-speckit-v1.0.0.zip` from committed HEAD; contents verified (1185 bytes extension.yml, all three command files).
- Three commands discovered: PASS — `specify extension list` output shows "OpsMill Speckit Workflow (v1.0.0)" with 3 commands enabled:
  - `speckit.opsmill.extract` — Extract knowledge, guidelines, and ADRs from completed spec directories into the project documentation system.
  - `speckit.opsmill.retrospect` — Run a session retrospective that surfaces context-management gaps and routes them to approved follow-up actions.
  - `speckit.opsmill.summary` — Produce a flow-level timeline of the current Claude Code session in the active feature directory.
- Discovery command used: `specify extension list`
- Command files verified in scratch project at `.specify/extensions/opsmill/commands/{extract,retrospect,summary}.md`.