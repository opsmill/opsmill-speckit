# reconcile-opsmill

A spec-kit preset that **overrides** `speckit.reconcile.run` — the drift-fixing command provided by the [stn1slv/spec-kit-reconcile](https://github.com/stn1slv/spec-kit-reconcile) extension — with the OpsMill-maintained command body. The command is a post-implementation gap closer: it takes a natural-language gap report, surgically updates the feature's `spec.md` and `plan.md`, and appends remediation tasks (`T###`) to `tasks.md`.

v1.0.0 ships the upstream command body **verbatim** as the baseline; OpsMill-specific adaptations to our repo structure land in later releases of this preset without touching the upstream extension.

## Prerequisite: the `reconcile` extension

Preset overrides of extension commands only register when the target extension is installed (`specify` checks for `.specify/extensions/reconcile/`). Install the upstream extension first:

```bash
specify extension add reconcile \
  --from https://github.com/stn1slv/spec-kit-reconcile/archive/refs/heads/main.zip
```

If the extension is absent when the preset is added, the `speckit.reconcile.run` override is silently skipped.

## Install

```bash
specify preset add reconcile-opsmill \
  --from https://github.com/opsmill/opsmill-speckit/archive/refs/heads/main.zip \
  --subdir presets/reconcile-opsmill
```

Local development install (from a working tree):

```bash
specify preset add --dev ./presets/reconcile-opsmill
```

After install, the preset's files live at `.specify/presets/reconcile-opsmill/` in the consumer repo, and `/speckit.reconcile.run` resolves to this preset's command body instead of the extension's.

## Usage

Provide a plain-text gap report describing the implementation drift:

```bash
/speckit.reconcile.run "Backend exists, but React screen is unreachable; need sidebar link and route"
```

Optional scope flags: `--spec-only`, `--plan-only`, `--tasks-only`.

## Provenance

The command body is a verbatim lift of `commands/reconcile.md` from
[stn1slv/spec-kit-reconcile](https://github.com/stn1slv/spec-kit-reconcile)
at commit `886f1dd` (identical to the copy vendored in
`opsmill/styrmin/.specify/extensions/reconcile/`). Upstream is MIT-licensed
by Stanislav Deviatov; the license ships alongside in
[`LICENSE`](LICENSE).
