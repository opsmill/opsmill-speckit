#!/usr/bin/env bash
#
# bootstrap.sh — set up (or update) a repository to OpsMill spec-kit standards.
#
# Idempotently brings the current repository onto spec-kit plus the OpsMill
# house extension set, using the OpsMill directory layout:
#
#   .agents/            <- canonical (real) directories
#   .claude/skills   -> ../.agents/skills      (symlink)
#   .claude/commands -> ../.agents/commands    (symlink)
#   .claude/rules    -> ../.agents/rules       (symlink)
#   AGENTS.md           <- canonical context file
#   CLAUDE.md        -> AGENTS.md               (symlink)
#
# The script is SAFE TO RE-RUN. It preserves existing spec-kit init state,
# never modifies an existing CLAUDE.md / AGENTS.md, and only converts a
# directory into a symlink after migrating its contents into canonical
# .agents/. The extension set is (re)installed from main on every run, so a
# re-run UPDATES the OpsMill extensions in place.
#
# Usage — run inside the repository you want to bootstrap or update:
#   cd /path/to/repo
#   curl -fsSL https://raw.githubusercontent.com/opsmill/opsmill-speckit/main/bootstrap.sh -o bootstrap.sh
#   bash bootstrap.sh
#   rm bootstrap.sh
#
# Requirements: git, and either an existing `specify` on PATH or `uv` to
# install spec-kit automatically.
#
set -euo pipefail

# --------------------------------------------------------------------------
# Configuration (override via environment variables)
# --------------------------------------------------------------------------
INTEGRATION="${INTEGRATION:-claude}"
# Optional spec-kit version pin for auto-install, e.g. "@v0.11.9". Empty = latest.
SPECKIT_PIN="${SPECKIT_PIN:-}"

# Extension id  ->  install source passed to `specify extension add --from`.
# agent-context ships with `specify init`, so it is not listed here.
OPSMILL_FROM="${OPSMILL_FROM:-https://github.com/opsmill/opsmill-speckit/archive/refs/heads/main.zip}"
REVIEW_FROM="${REVIEW_FROM:-https://github.com/ismaelJimenez/spec-kit-review/archive/refs/heads/main.zip}"
CRITIQUE_FROM="${CRITIQUE_FROM:-https://github.com/arunt14/spec-kit-critique/archive/refs/heads/main.zip}"

# .claude/<name> -> ../.agents/<name> symlinks that make up the house layout.
LINK_NAMES=(skills commands rules)

# Context files that must never be modified if they already exist. `specify
# init` may merge/overwrite these; we snapshot and restore them so existing
# content is preserved byte-for-byte. We never seed house content into them.
CONTEXT_FILES=(CLAUDE.md AGENTS.md)

# --------------------------------------------------------------------------
# Logging helpers
# --------------------------------------------------------------------------
step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info() { printf '  \033[34m•\033[0m %s\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
die()  { printf '  \033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# --------------------------------------------------------------------------
# Preflight
# --------------------------------------------------------------------------
step "Preflight"
command -v git >/dev/null 2>&1 || die "git is required"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || die "not inside a git repository — cd into the target repo first"
ok "repository: $(git rev-parse --show-toplevel)"

ensure_specify() {
  if command -v specify >/dev/null 2>&1; then
    ok "specify present: $(specify --version 2>/dev/null | head -n1)"
    return
  fi
  warn "specify not found — installing spec-kit"
  command -v uv >/dev/null 2>&1 \
    || die "spec-kit is missing and 'uv' is not available. Install uv (https://docs.astral.sh/uv/) or install spec-kit manually, then re-run."
  uv tool install specify-cli --from "git+https://github.com/github/spec-kit.git${SPECKIT_PIN}"
  command -v specify >/dev/null 2>&1 || die "specify still not on PATH after install"
  ok "specify installed: $(specify --version 2>/dev/null | head -n1)"
}
ensure_specify

# Record which context files existed BEFORE we touch anything. Used later to
# tell a user-authored CLAUDE.md (must be preserved) apart from one that
# `specify init` generates during this run (safe to replace with a symlink).
CLAUDE_PREEXISTED=0; AGENTS_PREEXISTED=0
[ -e CLAUDE.md ] && CLAUDE_PREEXISTED=1
[ -e AGENTS.md ] && AGENTS_PREEXISTED=1

# --------------------------------------------------------------------------
# Initialize spec-kit (idempotent: skip when already initialized)
# --------------------------------------------------------------------------
step "Initialize spec-kit"
if [ -d .specify ]; then
  ok ".specify/ already present — skipping init (nothing overwritten)"
else
  # Snapshot existing context files so init cannot alter them.
  declare -a _preserved=()
  for f in "${CONTEXT_FILES[@]}"; do
    if [ -f "$f" ]; then
      cp -p "$f" "${f}.speckit-bootstrap.bak"
      _preserved+=("$f")
    fi
  done

  info "specify init --here --integration $INTEGRATION"
  specify init --here --integration "$INTEGRATION" --script sh --ignore-agent-tools --force

  # Restore any pre-existing context file exactly as it was.
  for f in "${_preserved[@]}"; do
    mv -f "${f}.speckit-bootstrap.bak" "$f"
    info "preserved existing ${f} (left untouched)"
  done
  ok "spec-kit initialized"
fi

# --------------------------------------------------------------------------
# Apply the OpsMill layout: .agents/ canonical + .claude/ symlinks.
# Done BEFORE installing extensions so extension writes land in .agents/
# through the symlinks (verified behavior).
# --------------------------------------------------------------------------
step "Apply OpsMill layout (.agents canonical + .claude symlinks)"
mkdir -p .agents .claude
for name in "${LINK_NAMES[@]}"; do
  target=".agents/${name}"
  link=".claude/${name}"

  # Ensure the canonical directory exists (keep empty ones tracked).
  if [ ! -e "$target" ]; then
    mkdir -p "$target"
    : > "$target/.gitkeep"
  fi

  # Already the correct symlink? no-op.
  if [ -L "$link" ]; then
    if [ "$(readlink "$link")" = "../.agents/${name}" ]; then
      ok "${link} -> ../.agents/${name} (already linked)"
      continue
    fi
    warn "${link} is a symlink to '$(readlink "$link")' (unexpected) — leaving as-is"
    continue
  fi

  # A real directory (created by init/extensions)? migrate then link.
  if [ -d "$link" ]; then
    info "migrating ${link}/ into ${target}/"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --ignore-existing "${link}/" "${target}/"
    else
      cp -Rn "${link}/." "${target}/" 2>/dev/null || cp -R "${link}/." "${target}/"
    fi
    rm -rf "$link"
  elif [ -e "$link" ]; then
    warn "${link} exists and is not a directory — skipping"
    continue
  fi

  ln -s "../.agents/${name}" "$link"
  ok "${link} -> ../.agents/${name}"
done

# --------------------------------------------------------------------------
# Context files: AGENTS.md canonical, CLAUDE.md -> AGENTS.md.
# spec-kit's claude integration writes a real CLAUDE.md; the house convention
# makes AGENTS.md the source of truth with CLAUDE.md a symlink to it (mirroring
# the .agents/ -> .claude/ directory layout). Content is always preserved: a
# lone CLAUDE.md is promoted (moved) to AGENTS.md, never rewritten. When both
# already exist as real files we leave them untouched to avoid losing content.
# --------------------------------------------------------------------------
step "Context files (AGENTS.md canonical, CLAUDE.md -> AGENTS.md)"
if [ -L CLAUDE.md ]; then
  if [ "$(readlink CLAUDE.md)" = "AGENTS.md" ]; then
    ok "CLAUDE.md -> AGENTS.md (already linked)"
  else
    warn "CLAUDE.md is a symlink to '$(readlink CLAUDE.md)' (unexpected) — leaving as-is"
  fi
elif [ -f AGENTS.md ] && [ -f CLAUDE.md ]; then
  # Both are real files. If CLAUDE.md pre-existed it is user-authored — never
  # destroy it. Otherwise it was generated by `specify init` this run, so the
  # canonical AGENTS.md wins and CLAUDE.md becomes a symlink to it.
  if [ "$CLAUDE_PREEXISTED" = "1" ]; then
    warn "CLAUDE.md pre-existed alongside AGENTS.md — leaving both untouched (merge manually to link CLAUDE.md -> AGENTS.md)"
  else
    rm -f CLAUDE.md
    ln -s AGENTS.md CLAUDE.md
    ok "replaced generated CLAUDE.md with symlink -> AGENTS.md"
  fi
elif [ -f AGENTS.md ]; then
  ln -s AGENTS.md CLAUDE.md
  ok "CLAUDE.md -> AGENTS.md"
elif [ -f CLAUDE.md ]; then
  mv CLAUDE.md AGENTS.md
  ln -s AGENTS.md CLAUDE.md
  ok "promoted CLAUDE.md to AGENTS.md; CLAUDE.md -> AGENTS.md"
else
  info "no AGENTS.md/CLAUDE.md present — nothing to normalize"
fi

# --------------------------------------------------------------------------
# Install the OpsMill extension set: (re)installed from main on every run.
# --------------------------------------------------------------------------
step "Install OpsMill extension set"

is_installed() {
  # Extension ids are printed on their own indented line by `extension list`.
  specify extension list 2>/dev/null \
    | sed 's/\x1b\[[0-9;]*m//g' \
    | grep -qE "^[[:space:]]+$1[[:space:]]*$"
}

add_ext() {
  local id="$1" from="$2" out action
  if is_installed "$id"; then action="updating"; else action="installing"; fi
  info "${action} extension '${id}' from main"
  out="$(mktemp)"
  # --force pulls the latest from main and overwrites any existing install
  # (install-if-absent, update-in-place otherwise). `yes` auto-confirms the
  # trust prompt, fed via process substitution so its SIGPIPE exit status does
  # not trip `set -o pipefail`.
  if specify extension add "$id" --from "$from" --force >"$out" 2>&1 < <(yes 2>/dev/null); then
    ok "extension '${id}' up to date (main)"
    rm -f "$out"
  else
    warn "failed to ${action} '${id}':"
    sed 's/^/      /' "$out" >&2
    rm -f "$out"
    die "extension ${action} failed for '${id}'"
  fi
}

add_ext opsmill  "$OPSMILL_FROM"
add_ext review   "$REVIEW_FROM"
add_ext critique "$CRITIQUE_FROM"

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
step "Done"
ok "spec-kit + OpsMill extensions are in place"
info "Installed extensions:"
specify extension list 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | grep '✓' || true
cat <<'EOF'

This script made no commits. Review and commit when ready:
  git status
  git diff
EOF
