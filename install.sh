#!/usr/bin/env bash
# Set up ideavalidator: venv, dependencies, .env, and install the /ideavalidator Claude Code skill.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"

echo "→ virtualenv + dependencies"
[ -d "$HERE/.venv" ] || "$PY" -m venv "$HERE/.venv"
"$HERE/.venv/bin/pip" install -q -r "$HERE/requirements.txt"

if [ ! -f "$HERE/.env" ]; then
  cp "$HERE/.env.example" "$HERE/.env" && chmod 600 "$HERE/.env"
  echo "→ created .env — add your GEMINI_API_KEY (https://aistudio.google.com/apikey)"
fi

SKILL_SRC="$HERE/.claude/skills/ideavalidator/SKILL.md"
SKILL_DST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/ideavalidator"
mkdir -p "$SKILL_DST"
sed "s|__IDEAVALIDATOR_HOME__|$HERE|g" "$SKILL_SRC" > "$SKILL_DST/SKILL.md"
echo "→ installed skill to $SKILL_DST (repo root: $HERE)"

echo "→ doctor"
"$HERE/.venv/bin/python" -m pipeline.cli doctor || true
echo
echo "Done. In Claude Code run:  /ideavalidator <your idea in one line>"
