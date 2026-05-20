# Changelog — preset `taskstoissues-jira`

Release history for the `taskstoissues-jira` spec-kit preset
(`presets/taskstoissues-jira/preset.yml`). The version stream is
independent of the `opsmill` extension at the repo root; that extension
tracks its own releases in [`../../CHANGELOG.md`](../../CHANGELOG.md).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this artifact adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-20

### Added
- Initial release. Spec-kit preset (`schema_version: "1.0"`,
  `preset.id: "taskstoissues-jira"`, `requires.speckit_version: ">=0.8.0"`)
  that declares one command override under `provides.templates`:
  `type: command`, `name: speckit.taskstoissues`,
  `file: commands/speckit.taskstoissues.md`,
  `replaces: speckit.taskstoissues` (default `replace` strategy).
  Installable independently of the `opsmill` extension via
  `specify preset add taskstoissues-jira --subdir presets/taskstoissues-jira`.
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
