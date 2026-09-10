#!/bin/bash
# check-leaks.sh — run manually before staging (git add) and again right before
# git push. Doesn't fix anything, doesn't commit or push anything itself —
# it just scans working files and tells you what's about to go public.

set -uo pipefail
FOUND_BLOCKER=0

echo "== Checking for the live n8n production host =="
if grep -rn "nn.ehomedn.cc" . --include="*.json" --include="*.html" --include="*.js" --exclude-dir=.git; then
    echo "BLOCKED: live production host found above. Redact before committing/pushing."
    FOUND_BLOCKER=1
else
    echo "OK - no live host found."
fi

echo ""
echo "== All other embedded URLs found (review by eye - most of these are fine) =="
grep -rnEo "https?://[^\"'\\ ]+" . --include="*.json" --include="*.html" --include="*.js" --exclude-dir=.git \
    | grep -v "github.com\|githubusercontent.com\|shields.io\|fonts.googleapis.com\|fonts.gstatic.com\|schema.org" \
    | sort -u

echo ""
if [ "$FOUND_BLOCKER" -eq 1 ]; then
    echo "RESULT: leak-check FAILED - do not commit/push until the host above is redacted."
    exit 1
else
    echo "RESULT: no blockers. Skim the URL list above once, then it's safe to proceed."
    exit 0
fi
