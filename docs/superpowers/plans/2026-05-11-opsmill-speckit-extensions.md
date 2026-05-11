# opsmill-speckit v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Post-execution note (2026-05-11):** Task 7's smoke test discovered that
> spec-kit's command-name pattern `speckit.{ext-id}.{cmd}` allows exactly
> ONE segment in `{cmd}` — no further dots. The `.run` suffix appears
> throughout this plan as a design assumption; the installer rejected those
> names. Final command names are `speckit.opsmill.extract`,
> `speckit.opsmill.retrospect`, `speckit.opsmill.summary` (no `.run`). Commits
> `1699c96` corrected `extension.yml`; `ef656f6` aligned the README, the
> CHANGELOG Added/Provenance sections, and the two command-body
> self-references (extract.md L255, summary.md L62). All `.run`-suffixed
> command names below are stale design copy — read them without the suffix
> when comparing against the shipped artifact.

**Goal:** Ship `opsmill-speckit` v1 as a single spec-kit extension (`id: opsmill`) providing three OpsMill-owned commands (`speckit.opsmill.extract.run`, `.retrospect.run`, `.summary.run`) lifted verbatim from `../styrmin/.specify/extensions/`, installable via `specify extension add opsmill --from <zip>`.

**Architecture:** One `extension.yml` at the repo root declares three commands; one `commands/*.md` body per command (copied from styrmin, with two surgical name rewrites); README/CHANGELOG document install and provenance. No scripts vendored — `check-prerequisites.sh` ships with spec-kit core and is declared as a dependency. Manual smoke test only; no CI/release automation in v1.

**Tech Stack:** spec-kit ≥0.8.0 extension format (`extension.yml` schema 1.0), Markdown command bodies, YAML manifest. No code; this is a content-and-manifest deliverable.

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `extension.yml` | create | Manifest: extension id `opsmill`, three commands, `requires.scripts: [check-prerequisites.sh]`. |
| `commands/extract.md` | create (copy + 1 rewrite) | Body for `speckit.opsmill.extract.run`. |
| `commands/retrospect.md` | create (copy verbatim) | Body for `speckit.opsmill.retrospect.run`. |
| `commands/summary.md` | create (copy + 1 rewrite) | Body for `speckit.opsmill.summary.run`. |
| `README.md` | create | Install instructions, per-command descriptions, provenance. |
| `CHANGELOG.md` | create | v1.0.0 entry naming the lift sources. |
| `LICENSE` | unchanged | Apache-2.0; already present. |

No `scripts/` directory. No tests directory.

**Canonical lift source:** `../styrmin/.specify/extensions/`. Plan assumes the executor's working directory is `/Users/bkohler/automation/opsmill/opsmill-speckit/` and the styrmin sibling repo is at `/Users/bkohler/automation/opsmill/styrmin/` (same as the design phase).

---

## Task 1: Create commands directory and copy retrospect body verbatim

This is the cleanest of the three lifts (no rewrites) and validates the source path before tackling the two that need edits.

**Files:**
- Create: `commands/retrospect.md` (175 lines, copy of `../styrmin/.specify/extensions/retrospect/commands/retrospect.md`)

- [ ] **Step 1: Create the commands/ directory**

```bash
mkdir -p commands
```

- [ ] **Step 2: Copy retrospect.md verbatim**

```bash
cp ../styrmin/.specify/extensions/retrospect/commands/retrospect.md commands/retrospect.md
```

- [ ] **Step 3: Verify copy is byte-identical**

```bash
diff ../styrmin/.specify/extensions/retrospect/commands/retrospect.md commands/retrospect.md
```

Expected: no output (files identical, exit code 0).

- [ ] **Step 4: Verify no command-name references that need rewriting**

```bash
grep -nE 'speckit\.(retrospect|opsmill\.retrospect)' commands/retrospect.md || echo "clean"
```

Expected: `clean` (no match — body never references its own command name).

- [ ] **Step 5: Commit**

```bash
git add commands/retrospect.md
git commit -m "feat: lift retrospect command body from styrmin

Verbatim copy from ../styrmin/.specify/extensions/retrospect/commands/retrospect.md.
No rewrites; body has no self-name references.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Copy extract body and rewrite the one self-reference

The extract command body references its own command name in one line of output template (line 255). Lift + targeted Edit.

**Files:**
- Create: `commands/extract.md` (340 lines, copy of `../styrmin/.specify/extensions/extract/commands/extract.md` with one line edited)

- [ ] **Step 1: Copy extract.md from source**

```bash
cp ../styrmin/.specify/extensions/extract/commands/extract.md commands/extract.md
```

- [ ] **Step 2: Verify the source line that needs rewriting is at the expected line and value**

```bash
sed -n '255p' commands/extract.md
```

Expected output:

```
**Extracted by**: speckit.extract
```

If line content differs (source has drifted), STOP and report the actual content before proceeding. Do not blindly edit a different line.

- [ ] **Step 3: Apply the surgical rewrite**

Use the Edit tool (preferred — exact-string replacement). The unique old_string includes enough context that there is exactly one match in the file:

```
old_string: **Extracted by**: speckit.extract
new_string: **Extracted by**: speckit.opsmill.extract.run
```

- [ ] **Step 4: Verify the rewrite landed**

```bash
grep -n 'Extracted by' commands/extract.md
```

Expected output:

```
255:**Extracted by**: speckit.opsmill.extract.run
```

- [ ] **Step 5: Verify no stray `speckit.extract` references remain**

```bash
grep -nE 'speckit\.extract([^.]|$)' commands/extract.md || echo "clean"
```

Expected: `clean`. (The regex matches `speckit.extract` not followed by `.` — so `speckit.opsmill.extract.run` is fine but a bare `speckit.extract` would be flagged.)

- [ ] **Step 6: Confirm the rest of the file is byte-identical to source modulo line 255**

```bash
diff ../styrmin/.specify/extensions/extract/commands/extract.md commands/extract.md
```

Expected output (one-line diff at 255):

```
255c255
< **Extracted by**: speckit.extract
---
> **Extracted by**: speckit.opsmill.extract.run
```

- [ ] **Step 7: Commit**

```bash
git add commands/extract.md
git commit -m "feat: lift extract command body, namespace self-reference

Copy from ../styrmin/.specify/extensions/extract/commands/extract.md;
rewrite line 255 self-reference 'speckit.extract' to the namespaced
'speckit.opsmill.extract.run'. No other changes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Copy summary body and rewrite the one self-reference

The summary command body references its own command name once (line 62, inside an error-message backtick string). It also declares a `scripts:` block in its frontmatter — preserve that. Prose mentions of OTHER extensions' commands (`speckit.archive`, `speckit.reconcile.run` at lines 31-32) are deliberately left as-is — they reference third-party extensions, not commands this extension ships.

**Files:**
- Create: `commands/summary.md` (139 lines, copy of `../styrmin/.specify/extensions/summary/commands/run.md` with one line edited)

- [ ] **Step 1: Copy summary body from source (note the rename: source filename is `run.md`)**

```bash
cp ../styrmin/.specify/extensions/summary/commands/run.md commands/summary.md
```

- [ ] **Step 2: Verify the line that needs rewriting**

```bash
sed -n '62p' commands/summary.md
```

Expected output (one indented line — note the leading whitespace and the backtick wrapper):

```
     `No feature directory resolved from current branch — /speckit.summary.run requires an active feature branch.`
```

If line content or position differs, STOP and report.

- [ ] **Step 3: Apply the surgical rewrite**

Use Edit tool — the substring is unique:

```
old_string: /speckit.summary.run requires an active feature branch.
new_string: /speckit.opsmill.summary.run requires an active feature branch.
```

- [ ] **Step 4: Verify the rewrite landed**

```bash
grep -n 'speckit.opsmill.summary.run' commands/summary.md
```

Expected output:

```
62:     `No feature directory resolved from current branch — /speckit.opsmill.summary.run requires an active feature branch.`
```

- [ ] **Step 5: Verify the frontmatter scripts: block is preserved**

```bash
sed -n '1,7p' commands/summary.md
```

Expected output:

```
---
description: Produce a flow-level summary of the current Claude Code session — executive summary, chronological timeline, and outcomes — written into the active feature directory next to spec.md / plan.md.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --paths-only
  ps: scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
---

```

- [ ] **Step 6: Confirm only the one expected line differs from source**

```bash
diff ../styrmin/.specify/extensions/summary/commands/run.md commands/summary.md
```

Expected output (one-line diff at 62):

```
62c62
<      `No feature directory resolved from current branch — /speckit.summary.run requires an active feature branch.`
---
>      `No feature directory resolved from current branch — /speckit.opsmill.summary.run requires an active feature branch.`
```

- [ ] **Step 7: Confirm third-party prose mentions at L31-32 were LEFT alone**

```bash
sed -n '31,32p' commands/summary.md
```

Expected output:

```
granularity from `speckit.archive` (per-feature, permanent) and
`speckit.reconcile.run` (drift-fixing).
```

- [ ] **Step 8: Commit**

```bash
git add commands/summary.md
git commit -m "feat: lift summary command body, namespace self-reference

Copy from ../styrmin/.specify/extensions/summary/commands/run.md
(renamed run.md -> summary.md to match command verb); rewrite line 62
self-reference '/speckit.summary.run' to '/speckit.opsmill.summary.run'.
Preserve frontmatter scripts: block and prose mentions of third-party
extensions (speckit.archive, speckit.reconcile.run).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Write extension.yml

The manifest. Single source of truth for what spec-kit installs.

**Files:**
- Create: `extension.yml` (repo root)

- [ ] **Step 1: Write extension.yml**

Use the Write tool. Exact content:

```yaml
schema_version: "1.0"

extension:
  id: "opsmill"
  name: "OpsMill Speckit Workflow"
  version: "1.0.0"
  description: "OpsMill house spec-kit commands: knowledge extraction, session retrospective, and session summary."
  author: "opsmill"
  repository: "https://github.com/opsmill/opsmill-speckit"
  license: "Apache-2.0"
  homepage: "https://github.com/opsmill/opsmill-speckit"

requires:
  speckit_version: ">=0.8.0"
  scripts:
    - "check-prerequisites.sh"

provides:
  commands:
    - name: "speckit.opsmill.extract.run"
      file: "commands/extract.md"
      description: "Extract knowledge, guidelines, and ADRs from completed spec directories into the project documentation system."
    - name: "speckit.opsmill.retrospect.run"
      file: "commands/retrospect.md"
      description: "Run a session retrospective that surfaces context-management gaps and routes them to approved follow-up actions."
    - name: "speckit.opsmill.summary.run"
      file: "commands/summary.md"
      description: "Produce a flow-level timeline of the current Claude Code session in the active feature directory."

tags:
  - "opsmill"
  - "extract"
  - "retrospect"
  - "summary"
  - "workflow"
```

- [ ] **Step 2: Validate YAML parses**

```bash
python3 -c "import yaml,sys; yaml.safe_load(open('extension.yml'))" && echo OK
```

Expected: `OK`.

If python3 is unavailable on this machine, fall back to:

```bash
ruby -ryaml -e "YAML.load_file('extension.yml')" && echo OK
```

- [ ] **Step 3: Confirm every `provides.commands[].file` path resolves to a real file**

```bash
python3 - <<'PY'
import yaml, os, sys
m = yaml.safe_load(open('extension.yml'))
missing = [c['file'] for c in m['provides']['commands'] if not os.path.isfile(c['file'])]
if missing:
    print("MISSING:", missing); sys.exit(1)
print("All command files present.")
PY
```

Expected: `All command files present.`

- [ ] **Step 4: Confirm command names follow the `speckit.{ext-id}.{cmd}` pattern**

```bash
python3 - <<'PY'
import yaml, re, sys
m = yaml.safe_load(open('extension.yml'))
ext_id = m['extension']['id']
pat = re.compile(rf'^speckit\.{re.escape(ext_id)}\.[a-z][a-z0-9.\-]*$')
bad = [c['name'] for c in m['provides']['commands'] if not pat.match(c['name'])]
if bad:
    print("BAD:", bad); sys.exit(1)
print("All command names match speckit.{ext-id}.{cmd} pattern.")
PY
```

Expected: `All command names match speckit.{ext-id}.{cmd} pattern.`

- [ ] **Step 5: Commit**

```bash
git add extension.yml
git commit -m "feat: add extension.yml manifest

Declare the opsmill extension with three commands
(speckit.opsmill.extract.run, .retrospect.run, .summary.run) and
the check-prerequisites.sh script dependency (provided by spec-kit
core; not vendored).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Write README.md

Documents what this is, how to install it, and what each command does. Folds in per-command descriptions from each source extension's README.

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Use the Write tool. Exact content:

```markdown
# opsmill-speckit

OpsMill house [spec-kit](https://github.com/github/spec-kit) extension. Ships
three workflow commands under the `opsmill` namespace:

- `/speckit.opsmill.extract.run` — extract durable knowledge, guidelines, and
  ADRs from completed spec directories into `dev/knowledge/`, `dev/guidelines/`,
  `dev/adr/`.
- `/speckit.opsmill.retrospect.run` — run a session retrospective that surfaces
  context-management gaps and routes them to `fix-now`, `open-pr`,
  `github-issue`, or `local-only` dispositions.
- `/speckit.opsmill.summary.run` — produce a flow-level timeline of the current
  Claude Code session next to `spec.md` / `plan.md` in the active feature
  directory.

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
specify extension add opsmill --dev /path/to/opsmill-speckit
```

## Commands

### `/speckit.opsmill.extract.run`

Analyzes one or more completed spec directories and extracts durable knowledge
into the project's documentation system (`dev/knowledge/`, `dev/guidelines/`,
`dev/adr/`), then marks each spec as extracted.

Accepts multiple specs as space-separated arguments and processes them
sequentially.

### `/speckit.opsmill.retrospect.run`

Runs a retrospective on the current agent session while the work is still
fresh in context. Identifies concrete improvements to the repository's
context-management surface area (`AGENTS.md`, `CLAUDE.md`,
`.claude/settings.json`, `.agents/skills/`, `.agents/commands/`,
`.specify/templates/`, `dev/knowledge/`, `dev/guides/`, `dev/guidelines/`,
`dev/adr/`) and routes them through user-approved dispositions.

Stays read-only until the user approves each disposition bucket.

### `/speckit.opsmill.summary.run`

Produces a flow-level summary of the current Claude Code session — executive
summary, chronological timeline, and outcomes — written into the active
feature directory next to `spec.md` / `plan.md`.

Supports `--since <commit|time>` to bound the summary window.

## Provenance

Command bodies in v1 are verbatim lifts from
`opsmill/styrmin/.specify/extensions/`:

- `commands/extract.md` ← `extract/commands/extract.md`
- `commands/retrospect.md` ← `retrospect/commands/retrospect.md`
- `commands/summary.md` ← `summary/commands/run.md`

Two surgical line edits update self-references to the namespaced form
(`speckit.opsmill.<cmd>.run`); no other content changes. See `CHANGELOG.md`
for the exact lines.

## License

Apache-2.0. See `LICENSE`.
```

- [ ] **Step 2: Verify install command names match `extension.yml`**

```bash
python3 - <<'PY'
import yaml
m = yaml.safe_load(open('extension.yml'))
expected_id = m['extension']['id']
with open('README.md') as f:
    readme = f.read()
assert f"specify extension add {expected_id}" in readme, "README install command missing or wrong extension id"
print("README install matches extension.yml id:", expected_id)
PY
```

Expected: `README install matches extension.yml id: opsmill`

- [ ] **Step 3: Confirm every command name documented in the README is also declared in `extension.yml`**

```bash
python3 - <<'PY'
import yaml, re, sys
m = yaml.safe_load(open('extension.yml'))
declared = {c['name'] for c in m['provides']['commands']}
with open('README.md') as f:
    readme = f.read()
# README uses leading-slash form (/speckit.opsmill.X.run)
documented = set(re.findall(r'/(speckit\.opsmill\.[a-z.]+)', readme))
extra = documented - declared
missing = declared - documented
if extra: print("README mentions undeclared commands:", extra); sys.exit(1)
if missing: print("README missing commands declared in manifest:", missing); sys.exit(1)
print("README ↔ manifest command list aligned:", sorted(declared))
PY
```

Expected: `README ↔ manifest command list aligned: ['speckit.opsmill.extract.run', 'speckit.opsmill.retrospect.run', 'speckit.opsmill.summary.run']`

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with install instructions and command index

Document the three commands, install paths (main, tagged release,
local --dev), the check-prerequisites.sh dependency, and provenance
from styrmin.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Write CHANGELOG.md

Records the v1.0.0 release contents and provenance.

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write CHANGELOG.md**

Use the Write tool. Exact content:

```markdown
# Changelog

All notable changes to opsmill-speckit are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-11

### Added
- Initial release. Single spec-kit extension (`id: opsmill`,
  `schema_version: "1.0"`, `requires.speckit_version: ">=0.8.0"`) providing:
  - `speckit.opsmill.extract.run` — knowledge / guidelines / ADR extraction
    from completed spec directories.
  - `speckit.opsmill.retrospect.run` — session retrospective with
    user-approved disposition routing.
  - `speckit.opsmill.summary.run` — flow-level session summary in the
    active feature directory.
- `requires.scripts: ["check-prerequisites.sh"]` declared (script is shipped
  by spec-kit core; not vendored here).

### Provenance
Command bodies are lifted from `opsmill/styrmin/.specify/extensions/`:
- `commands/extract.md` from `extract/commands/extract.md`. Single edit:
  line 255 self-reference `speckit.extract` rewritten to
  `speckit.opsmill.extract.run`.
- `commands/retrospect.md` from `retrospect/commands/retrospect.md`.
  Verbatim, no edits.
- `commands/summary.md` from `summary/commands/run.md` (renamed). Single
  edit: line 62 self-reference `/speckit.summary.run` rewritten to
  `/speckit.opsmill.summary.run`.
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG with v1.0.0 entry and provenance

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Manual smoke test (local zip install)

Validates the extension installs and exposes all three commands. No automated
test harness in v1; this is a one-shot manual gate.

**Files:** none modified by this task.

- [ ] **Step 1: Build a local ZIP of the working tree**

```bash
mkdir -p /tmp/opsmill-speckit-smoke
git archive --format=zip --prefix=opsmill-speckit/ HEAD -o /tmp/opsmill-speckit-smoke/opsmill-speckit-v1.0.0.zip
unzip -l /tmp/opsmill-speckit-smoke/opsmill-speckit-v1.0.0.zip | grep -E '(extension\.yml|commands/)' | head -10
```

Expected: the listing shows `opsmill-speckit/extension.yml`, `opsmill-speckit/commands/extract.md`, `opsmill-speckit/commands/retrospect.md`, `opsmill-speckit/commands/summary.md`.

- [ ] **Step 2: Create a scratch spec-kit project**

```bash
mkdir -p /tmp/opsmill-speckit-smoke/scratch && cd /tmp/opsmill-speckit-smoke/scratch
specify init --here --no-git --ai claude
```

(If `specify init` syntax differs in the installed spec-kit version, fall back to whatever the installed version's init flow is. The goal is a directory with `.specify/` initialized.)

Expected: directory now contains `.specify/`.

- [ ] **Step 3: Install opsmill extension from the local ZIP**

```bash
specify extension add opsmill --from /tmp/opsmill-speckit-smoke/opsmill-speckit-v1.0.0.zip
```

Expected: spec-kit reports install success.

If the installer errors on `requires.scripts: [check-prerequisites.sh]` (e.g. script not found in the scratch project's spec-kit init), this is informative but non-blocking for v1 — record the error in the smoke-test notes and proceed to step 4. If the installer rejects the manifest schema outright, STOP and report.

- [ ] **Step 4: Discover the three commands**

```bash
specify extension list
```

(If `specify extension list` isn't the correct verb, try `specify extension show opsmill` or `specify list` and substitute the documented form.)

Expected: output mentions `opsmill` extension with three commands matching:
- `speckit.opsmill.extract.run`
- `speckit.opsmill.retrospect.run`
- `speckit.opsmill.summary.run`

- [ ] **Step 5: Confirm the command bodies were copied into the agent's command directory**

spec-kit installs extension commands into the detected agent directory
(`.claude/commands/`, `.agents/commands/`, etc., depending on which agent was
selected at `specify init`). Locate the install path and confirm:

```bash
find . -name 'speckit.opsmill.*' -type f | sort
```

Expected: three files found, one per command.

- [ ] **Step 6: Record the smoke-test result**

Write a one-line outcome to the original opsmill-speckit working tree:

```bash
cd /Users/bkohler/automation/opsmill/opsmill-speckit
{
  echo ""
  echo "## Smoke test — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "- ZIP install: PASS / FAIL — <details>"
  echo "- Three commands discovered: PASS / FAIL — <details>"
  echo "- Discovery command used: \`specify ...\`"
} >> CHANGELOG.md
```

Fill in PASS/FAIL and the details before committing.

- [ ] **Step 7: Commit smoke-test record**

```bash
git add CHANGELOG.md
git commit -m "chore: record v1.0.0 smoke-test outcome in CHANGELOG

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 8: Clean up scratch dir**

```bash
rm -rf /tmp/opsmill-speckit-smoke
```

---

## Task 8: Final repo-level verification

Sanity sweep before declaring v1 ready to tag.

**Files:** none modified by this task.

- [ ] **Step 1: All expected files present**

```bash
ls -1 extension.yml README.md CHANGELOG.md LICENSE commands/extract.md commands/retrospect.md commands/summary.md
```

Expected: seven lines listed, no `No such file` errors.

- [ ] **Step 2: extension.yml still parses and `provides.commands[].file` paths still resolve**

```bash
python3 - <<'PY'
import yaml, os, sys
m = yaml.safe_load(open('extension.yml'))
missing = [c['file'] for c in m['provides']['commands'] if not os.path.isfile(c['file'])]
if missing:
    print("MISSING:", missing); sys.exit(1)
print("OK:", m['extension']['id'], m['extension']['version'])
PY
```

Expected: `OK: opsmill 1.0.0`

- [ ] **Step 3: No accidental backup/swap files committed**

```bash
git ls-files | grep -E '\.(bak|swp|orig)$' && echo "FOUND" || echo "clean"
```

Expected: `clean`.

- [ ] **Step 4: Working tree clean**

```bash
git status --porcelain
```

Expected: empty output.

- [ ] **Step 5: (User-initiated) Tag v1.0.0**

The plan stops here. Tagging and pushing are user-initiated:

```bash
# Run only when you (the user) are ready to publish:
git tag v1.0.0
git push origin main --tags
```

The README and CHANGELOG already document v1.0.0; the tag activates the
`/archive/refs/tags/v1.0.0.zip` install URL.

---

## Self-Review

**Spec coverage:** each Design subsection in the spec maps to a task:

- "Repo layout" → Tasks 1, 2, 3, 4, 5, 6 (one file each).
- "`extension.yml`" → Task 4.
- "Install (consumer side)" → Task 5 (README documents the install).
- "Provenance and content rules" → Tasks 1, 2, 3 (the three lifts + two
  surgical rewrites enumerated in the spec).
- "Licensing" → handled implicitly: repo LICENSE unchanged; README references
  it; no per-file license headers added.
- "Validation" → Task 7.
- "Open question (carried into plan execution): discovery command name" →
  Task 7 Step 4 has the fallback instruction.

**Placeholder scan:** no TBD/TODO/`<fill in>`/`appropriate error handling`
phrases. Smoke-test outcome (Task 7 Step 6) intentionally requires the
executor to fill in PASS/FAIL — that's an observed-result substitution, not a
placeholder for unspecified design.

**Type/name consistency:**
- Extension id `opsmill` is used identically in `extension.yml`, README
  install commands, and Task 7 install step.
- Command names use `speckit.opsmill.{extract,retrospect,summary}.run`
  consistently throughout (`extension.yml`, body rewrites, README, CHANGELOG,
  smoke-test discovery).
- File paths `commands/{extract,retrospect,summary}.md` match between
  `extension.yml` `provides.commands[].file`, the cp targets, and the README
  provenance list.
- Source paths `../styrmin/.specify/extensions/{extract,retrospect,summary}/commands/{extract,retrospect,run}.md` match between the spec's provenance
  table and the Task 1/2/3 cp commands. Note the source filename for summary
  is `run.md` (not `summary.md`); the rename to `commands/summary.md` is
  intentional and called out in Task 3 Step 1 and the README provenance.
