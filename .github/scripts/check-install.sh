#!/usr/bin/env bash
# Install the opsmill extension and both presets from this working tree into a
# fresh spec-kit project, following the README install order, and check that
# every command registers.
#
# Usage: .github/scripts/check-install.sh
# Runs the `specify` on PATH; set SPECIFY to use another one, for example
#   SPECIFY="uvx --from specify-cli==0.11.9 specify" .github/scripts/check-install.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPECIFY="${SPECIFY:-specify}"
# Same pin as the README install of the reconcile extension.
RECONCILE_URL="https://github.com/stn1slv/spec-kit-reconcile/archive/886f1dd.zip"

PROJECT="$(mktemp -d)"
trap 'rm -rf "$PROJECT"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

manifest_version() {
  sed -n 's/^  version: "\(.*\)"$/\1/p' "$1"
}

cd "$PROJECT"
git init -q
$SPECIFY version
$SPECIFY init --here --integration claude --script sh --ignore-agent-tools --force >/dev/null

echo "--- extension: opsmill"
$SPECIFY extension add --dev "$REPO_ROOT"
ext_version="$(manifest_version "$REPO_ROOT/extension.yml")"
extensions="$($SPECIFY extension list)"
grep -qF "OpsMill Speckit Workflow (v$ext_version)" <<<"$extensions" ||
  fail "opsmill v$ext_version is not in 'specify extension list'"
for path in presets .github; do
  [ ! -e ".specify/extensions/opsmill/$path" ] ||
    fail "$path/ was copied into .specify/extensions/opsmill/ (check .extensionignore)"
done
commands="$(sed -n 's/^ *- name: "speckit\.opsmill\.\(.*\)"$/\1/p' "$REPO_ROOT/extension.yml")"
[ -n "$commands" ] || fail "no speckit.opsmill.* command found in extension.yml"
for cmd in $commands; do
  [ -f ".claude/skills/speckit-opsmill-$cmd/SKILL.md" ] ||
    fail "speckit.opsmill.$cmd did not register as a Claude skill"
done

echo "--- extension: reconcile (required by reconcile-opsmill)"
echo y | $SPECIFY extension add reconcile --from "$RECONCILE_URL"

for preset in taskstoissues-jira reconcile-opsmill; do
  echo "--- preset: $preset"
  $SPECIFY preset add --dev "$REPO_ROOT/presets/$preset"
  preset_version="$(manifest_version "$REPO_ROOT/presets/$preset/preset.yml")"
  presets="$($SPECIFY preset list)"
  grep -qF "($preset) v$preset_version" <<<"$presets" ||
    fail "$preset v$preset_version is not in 'specify preset list'"
done

# The overridden commands must carry the OpsMill body, not the original one.
grep -qF "dev/jira.yml" .claude/skills/speckit-taskstoissues/SKILL.md ||
  fail "speckit.taskstoissues does not use the taskstoissues-jira body"
grep -qF "dev/guidelines/" .claude/skills/speckit-reconcile-run/SKILL.md ||
  fail "speckit.reconcile.run does not use the reconcile-opsmill body"

echo "OK: opsmill v$ext_version and both presets installed"
