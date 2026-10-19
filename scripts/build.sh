#!/usr/bin/env bash
# Regenerates the two build outputs from their sources:
#   setup-script.sh      <- scripts/setup-script.tmpl.sh + global/CLAUDE.md (embedded)
#   dist/stack-core.zip  <- plugin/ (upload to claude.ai -> Customize -> Plugins)
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'EOF'
from pathlib import Path
tmpl = Path("scripts/setup-script.tmpl.sh").read_text()
md = Path("global/CLAUDE.md").read_text()
assert "CLAUDE_MD_EOF" not in md, "global/CLAUDE.md must not contain the heredoc delimiter"
Path("setup-script.sh").write_text(tmpl.replace("@@GLOBAL_CLAUDE_MD@@", md.rstrip("\n")))
EOF
chmod +x setup-script.sh
bash -n setup-script.sh

mkdir -p dist
rm -f dist/stack-core.zip
(cd plugin && zip -qr -X ../dist/stack-core.zip . -x '*/__pycache__/*' '*.pyc')
echo "built setup-script.sh ($(wc -l < setup-script.sh) lines) and dist/stack-core.zip ($(du -k dist/stack-core.zip | cut -f1) KB)"
