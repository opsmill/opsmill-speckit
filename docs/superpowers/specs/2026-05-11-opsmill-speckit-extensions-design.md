# opsmill-speckit — Centralize OpsMill-Owned Spec-Kit Extensions

**Status:** Draft (revised 2026-05-11 — vehicle switched from preset to extension)
**Date:** 2026-05-11
**Author:** Benoit Kohler

## Problem

OpsMill consumes spec-kit across multiple internal repos (`styrmin`, `infrahub-mcp`,
others). Each consumer currently inlines an identical `.specify/extensions/` tree
containing 12 extensions, three of which are OpsMill-authored (`extract`,
`retrospect`, `summary`) plus a fourth orchestrator (`auto`) that depends on
third-party peers. Maintaining these copies by hand drifts and duplicates work.

`infrahub-speckit` already demonstrates a working pattern for shipping a single
OpsMill-owned spec-kit repo to multiple consumers. We want the same developer
experience — one repo, one install command — for our cross-cutting (non-Infrahub)
workflow commands.

## Vehicle: extension, not preset

Per spec-kit's published guidance (`presets/README.md`, top-level `README.md`):

> Use an **extension** when the goal is to **add a brand-new command** or
> workflow, or to integrate an external tool or service. Use a **preset** to
> customize the format of specs, plans, or tasks, or to enforce organizational
> or regulatory standards.

`infrahub-speckit` is correctly a *preset* because it **wraps** the core
`speckit.specify` / `.plan` / `.implement` commands (composition strategy
`wrap`). It is not adding new top-level commands.

Our case adds three brand-new commands (`extract`/`retrospect`/`summary`). That
is the extension case. Preset composition strategies (`replace`, `prepend`,
`append`, `wrap`) all assume a lower-priority target to compose against; none
adds net-new top-level commands. We therefore ship this as a **single
namespaced extension** with `extension.id = "opsmill"`.

Consequence: spec-kit enforces the command-name pattern
`speckit.{ext-id}.{cmd}` for extensions. Today's command names
(`speckit.extract.run`, `speckit.retrospect.run`, `speckit.summary.run`) become
`speckit.opsmill.extract.run`, `speckit.opsmill.retrospect.run`,
`speckit.opsmill.summary.run`. The rename pain lands in the (already deferred)
consumer migration PR.

## Goals

1. Publish a single `opsmill-speckit` extension repo that ships the three
   OpsMill-owned commands as one installable artifact under the `opsmill`
   namespace.
2. One install command, one manifest, one release artifact — the same
   developer experience as `specify preset add` for `infrahub-speckit`.
3. Preserve authorship and command-body content of each source extension —
   v1 is a lift, not a rewrite.

## Non-goals (v1)

- The `auto` orchestrator. OpsMill-authored, but its `requires.commands` pulls
  in third-party peers (`critique.run`, `review`, `checkpoint.commit`).
  Deferred until those peers have a stable distribution story.
- Vendoring `tinyspec`. Disposition recorded for a future release: vendor
  as-is from `Quratulain-bilal/spec-kit-tinyspec` (MIT), preserve attribution,
  no modifications.
- The seven other third-party extensions present in `styrmin`/`infrahub-mcp`
  (`archive`, `checkpoint`, `critique`, `git`, `iterate`, `reconcile`,
  `review`). Each is consumed in-place by each repo; not OpsMill's to
  redistribute under our extension brand.
- Migrating `styrmin` and `infrahub-mcp` to consume the new extension. Separate
  follow-up work item. Both the file move and the command-name rewrite happen
  there.
- CI/release automation. Manual tag-and-zip is sufficient for v1.
- Hook wiring. None of the three commands has a natural auto-fire point — they
  are user-triggered. No hooks block in `extension.yml`.

## Source audit

OpsMill ownership audit of `styrmin/.specify/extensions/` (identical tree in
`infrahub-mcp`):

| ext          | author             | upstream                                   | included in v1 |
|--------------|--------------------|--------------------------------------------|----------------|
| `archive`    | Stanislav Deviatov | github.com/stn1slv/spec-kit-archive        | no             |
| `auto`       | OpsMill            | —                                          | no (deps)      |
| `checkpoint` | Aaron Sun          | github.com/aaronrsun/spec-kit-checkpoint   | no             |
| `critique`   | arunt14            | github.com/arunt14/spec-kit-critique       | no             |
| `extract`    | OpsMill            | —                                          | **yes**        |
| `git`        | spec-kit-core      | github.com/github/spec-kit                 | no             |
| `iterate`    | Vianca Martinez    | github.com/imviancagrace/spec-kit-iterate  | no             |
| `reconcile`  | Stanislav Deviatov | github.com/stn1slv/spec-kit-reconcile      | no             |
| `retrospect` | OpsMill            | —                                          | **yes**        |
| `review`     | Ismael Jimenez     | github.com/ismaelJimenez/spec-kit-review   | no             |
| `summary`    | opsmill            | (repo field points at opsmill/styrmin)     | **yes**        |
| `tinyspec`   | Quratulain-bilal   | github.com/Quratulain-bilal/spec-kit-tinyspec | no          |

## Design

### Repo layout

```
opsmill-speckit/
├── extension.yml
├── README.md
├── CHANGELOG.md
├── LICENSE                           # already present (Apache-2.0)
└── commands/
    ├── extract.md                    # body for speckit.opsmill.extract.run
    ├── retrospect.md                 # body for speckit.opsmill.retrospect.run
    └── summary.md                    # body for speckit.opsmill.summary.run
```

Flat `commands/` (not `.specify/extensions/<id>/commands/`) — this is the
extension's own root, not an embedded tree. Filenames track the verb part of
the command for legibility; the canonical mapping lives in `extension.yml`
via `provides.commands[].file`.

No `scripts/` directory: none of the three source extensions declare
`requires.scripts`.

No `ATTRIBUTION.md`: all three are OpsMill-authored.

### `extension.yml`

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
    - "check-prerequisites.sh"     # used by speckit.opsmill.summary.run

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

`speckit_version: ">=0.8.0"` matches the floor used by `infrahub-speckit`.
The three source `extension.yml` files declare `>=0.1.0`, but the actual
consumer environment (styrmin, infrahub-mcp) already requires 0.8.0 via
`infrahub-speckit`, so this floor is non-blocking.

`requires.scripts: ["check-prerequisites.sh"]` is declared because the
`summary` command body's frontmatter references the script via the spec-kit
`{SCRIPT}` placeholder. This script is shipped by spec-kit core (present at
`.specify/scripts/bash/check-prerequisites.sh` in any spec-kit-initialized
repo, including styrmin/infrahub-mcp) — we do **not** vendor a copy in this
extension. The declaration is informational so consumers know the dependency
exists.

No `requires.commands` or `requires.tools` — none of the three command bodies
invokes a peer slash command or external CLI tool.

### Install (consumer side)

```bash
# latest main
specify extension add opsmill \
  --from https://github.com/opsmill/opsmill-speckit/archive/refs/heads/main.zip

# pinned release
specify extension add opsmill \
  --from https://github.com/opsmill/opsmill-speckit/archive/refs/tags/v1.0.0.zip
```

The `<extension-name>` positional arg must match `extension.id` (`opsmill`)
per spec-kit's documented install pattern.

### Provenance and content rules

Canonical source: `../styrmin/.specify/extensions/`. The same tree exists
bit-identical in `../infrahub-mcp`; either is valid, but the plan and any
re-syncs use `styrmin` as the single source of truth.

For each command body:

1. Copy source file content verbatim from
   `../styrmin/.specify/extensions/<ext>/commands/<file>.md`:
   - `extract/commands/extract.md`  → `commands/extract.md`
   - `retrospect/commands/retrospect.md` → `commands/retrospect.md`
   - `summary/commands/run.md` → `commands/summary.md`
2. No content edits in v1 *to the prose*. The only modification is to update
   any front-matter or in-file references that would break under the renamed
   command identifier — see step 3.
3. Apply exactly these two surgical rewrites (audited by grep across the
   three source bodies — no others required):
   - `commands/extract.md` line 255: `**Extracted by**: speckit.extract` →
     `**Extracted by**: speckit.opsmill.extract.run`.
   - `commands/summary.md` line 62 (inside an error-message backtick string):
     `/speckit.summary.run` → `/speckit.opsmill.summary.run`.
   - `commands/retrospect.md`: no rewrites; copy verbatim.
   - Prose references to other extensions' commands (e.g. `speckit.archive`,
     `speckit.reconcile.run` in `commands/summary.md` lines 31-32) are
     **not** rewritten — they reference third-party extensions that
     consumers may or may not have installed alongside this one. Preserve
     content fidelity.
   - Keep `commands/summary.md` frontmatter `scripts:` block as-is.

For the README:

- Top section mirrors `infrahub-speckit/README.md` shape (purpose, install,
  what each command does).
- One subsection per command, content folded in from each source extension's
  README.md.

### Licensing

- Repo LICENSE is Apache-2.0 (already present).
- Each source extension is MIT.
- Decision: keep repo Apache-2.0. The Apache-2.0 license covers the manifest,
  README, packaging; the command bodies are prompt content carried under the
  same repo license. Source extensions were authored by OpsMill, so no
  third-party attribution is required.

### Validation

Manual smoke test only:

1. Build a local ZIP of the repo (`git archive` or zip of working tree).
2. From a scratch directory, run
   `specify extension add opsmill --from <path-to-local-zip>`.
3. Confirm spec-kit reports successful install and the three commands are
   discoverable via `specify extension list` (verify the exact discovery
   command name during plan execution — substitute the documented equivalent
   if `list` is wrong).
4. Invoke `speckit.opsmill.extract.run` against a fixture spec directory;
   confirm it loads without parsing errors. Body output is informational —
   the test is "install + load", not "full semantic correctness."

No automated test harness in v1.

## Resolved questions

(formerly "open questions" — addressed during plan writing)

1. **Vehicle: extension vs preset.** Resolved: extension. Preset's documented
   composition strategies (`replace`/`prepend`/`append`/`wrap`) all assume an
   existing target. Net-new commands are the extension case per spec-kit
   guidance.
2. **Command naming.** Resolved: spec-kit enforces `speckit.{ext-id}.{cmd}`
   for extensions, so commands become `speckit.opsmill.*`. The rename is
   absorbed by the deferred consumer-migration PR.

## Open question (carried into plan execution)

1. **Discovery command name.** Confirm whether installed extensions are listed
   via `specify extension list`, `specify list`, or a different verb. If wrong
   in the validation step, substitute the documented form.

## Post-execution note (2026-05-11)

Two findings from the Task 7 smoke test invalidated assumptions baked into
this document; the shipped artifact diverges from the design in these
specific ways:

1. **Command names dropped the `.run` suffix.** spec-kit's
   `speckit.{ext-id}.{cmd}` pattern allows exactly ONE segment after
   `{ext-id}` — no further dots. The design assumed `speckit.opsmill.extract.run`
   (etc.); the installer rejected those names. Final names are:
   `speckit.opsmill.extract`, `speckit.opsmill.retrospect`,
   `speckit.opsmill.summary`. See commits `1699c96` (manifest fix) and
   `ef656f6` (downstream alignment of READMEs and command-body
   self-references). All `extract.run` / `retrospect.run` / `summary.run`
   references in this spec should be read as `extract` / `retrospect` /
   `summary` instead.
2. **Discovery command resolved.** `specify extension list` is the correct
   verb (Open question 1 above, resolved by smoke test).

## Implementation outline (for plan phase)

1. Create `extension.yml` at repo root.
2. Create `commands/` with three files copied from the canonical styrmin
   source (rename per the rule).
3. Write `README.md` (install + commands sections) and `CHANGELOG.md` (v1.0.0
   entry naming the lift sources).
4. Build and verify a local ZIP installs and exposes the three commands in a
   scratch directory.
5. Tag `v1.0.0` (user-initiated; not part of automated steps in v1).

Each step is independent of the consumer migration; this design ships
`opsmill-speckit` standalone.
