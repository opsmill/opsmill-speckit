# taskstoissues-jira

A spec-kit preset that **overrides** the native `speckit.taskstoissues` command with a Jira-flavored implementation. One Jira issue is created per `## Phase N:` block in `tasks.md` (not per task line); inter-task `T<NNN>` mentions are resolved at phase granularity and emitted as `Blocks` issue links between phase issues (transitively reduced). All Atlassian traffic goes through the Atlassian MCP.

This preset is published from the same repo as the [`opsmill` extension](../../README.md), but the two are independent: install the preset alone if you only need the Jira workflow, or install both for the full OpsMill SDD experience.

## Install

```bash
specify preset add taskstoissues-jira \
  --from https://github.com/opsmill/opsmill-speckit/archive/refs/heads/main.zip \
  --subdir presets/taskstoissues-jira
```

Local development install (from a working tree):

```bash
specify preset add --dev ./presets/taskstoissues-jira
```

After install, the preset's files live at `.specify/presets/taskstoissues-jira/` in the consumer repo, and `/speckit.taskstoissues` resolves to this preset's command body.

## One-time setup (per consumer repo)

Consumer-specific Jira values live in **`dev/jira.yml`** at the repo root — not inside the preset's install dir — so `specify preset add taskstoissues-jira` updates never overwrite them.

1. Copy the example template into place:

   ```bash
   mkdir -p dev
   cp .specify/presets/taskstoissues-jira/templates/jira.example.yml dev/jira.yml
   ```

2. Edit `dev/jira.yml`:

   - `cloud` — your Atlassian site hostname (e.g. `acme.atlassian.net`). Matched against `getAccessibleAtlassianResources` to resolve `cloudId`.
   - `default_project_key` — your repo's Jira project key (the shipped placeholder `PROJ` aborts on purpose).
   - `custom_fields.epic_link` + `custom_fields.team` — real custom field IDs for your Jira instance. Resolve with `mcp__claude_ai_Atlassian__getJiraIssueTypeMetaWithFields` and replace each `customfield_XXXXX` placeholder.
   - Optionally override `default_issue_type` and `labels_default` (vendor defaults: `Task`, `[spec-kit]`).

3. Commit `dev/jira.yml`. The whole repo shares it.

The preset's own `config/jira.yml` (under `.specify/presets/taskstoissues-jira/`) ships only universal defaults (`default_issue_type`, `labels_default`) and is overwritten on every preset update — do not edit it.

## Per-contributor setup

Each contributor copies `.specify/presets/taskstoissues-jira/templates/overrides/example.yml` to `<your-email-slug>.yml` in the same directory (slug = `git config user.email` lowercased with every non-alphanumeric character replaced by `-`, e.g. `pol@opsmill.com` → `pol-opsmill-com.yml`) and fills in `assignee.email` plus `team.name`. Real override files are gitignored; only `example.yml` and the README are tracked.

## Epic resolution

The command parses the current branch name for `<default_project_key>-\d+` (case-insensitive), falling back to `$ARGUMENTS`, then to an interactive prompt. The matched key is validated as an Epic via `getJiraIssue`.

## Failure mode

The run stops at the first `createJiraIssue` / `createIssueLink` error and prints the partial `phase_number → IssueKey` map. The command is **not** idempotent — delete the listed issues in Jira manually before retrying.

## Provenance

Ported from the Infrahub preset introduced in [opsmill/infrahub#9208](https://github.com/opsmill/infrahub/pull/9208). Generalized for cross-repo reuse: the Infrahub-specific project key (`IFC`) and custom field IDs become placeholders driven by `config/jira.yml`.
