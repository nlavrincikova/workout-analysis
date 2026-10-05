#!/bin/bash
# check-leaks.sh — run manually before staging (git add) and again right before
# git push. Doesn't fix anything, doesn't commit or push anything itself —
# it just scans working files and tells you what's about to go public.
#
# Two kinds of check:
#   1. Generic patterns (this file) — need no secrets, safe to publish with the repo.
#   2. Private literals — the real host and webhook IDs live in ~/.leak-patterns, one per
#      line, and NEVER in this repo: this script is public, so it must not contain them.
#      Override the location with LEAK_PATTERNS_FILE.

set -uo pipefail
FOUND_BLOCKER=0

# Scripts are in scope on purpose: a checker that can't see its own file is how a secret ends up inside it.
SCAN=(--include="*.json" --include="*.html" --include="*.js" --include="*.md" --include="*.py" --include="*.sh" --include="*.ps1" --exclude-dir=.git)
PRIVATE_PATTERNS="${LEAK_PATTERNS_FILE:-$HOME/.leak-patterns}"

echo "== Checking for private literals (live host, real webhook IDs) =="
if [ -f "$PRIVATE_PATTERNS" ]; then
    if grep -rniF -f <(tr -d '\r' < "$PRIVATE_PATTERNS" | grep -v '^[[:space:]]*\(#\|$\)') . "${SCAN[@]}"; then
        echo "BLOCKED: a private literal from $PRIVATE_PATTERNS was found above. Redact before committing/pushing."
        FOUND_BLOCKER=1
    else
        echo "OK - none of the private literals found."
    fi
else
    echo "WARNING: $PRIVATE_PATTERNS not found - the live host and real webhook IDs were NOT checked (the generic checks below still ran)."
fi

echo ""
echo "== Checking for unredacted webhook IDs (any value other than the placeholder) =="
WEBHOOK_HITS=$(
    {
        grep -rnE '"webhookId"[[:space:]]*:[[:space:]]*"' . --include="*.json" --exclude-dir=.git | grep -v 'REDACTED-REGENERATED-ON-IMPORT'
        grep -rniE 'webhook(-test)?/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' . "${SCAN[@]}"
    }
)
if [ -n "$WEBHOOK_HITS" ]; then
    echo "$WEBHOOK_HITS"
    echo "BLOCKED: unredacted webhook ID found above. Replace it with the REDACTED-REGENERATED-ON-IMPORT / YOUR-...-WEBHOOK-ID placeholder."
    FOUND_BLOCKER=1
else
    echo "OK - no unredacted webhook IDs found."
fi

echo ""
echo "== All other embedded URLs found (review by eye - most of these are fine) =="
grep -rnEo "https?://[^\"'\\ ]+" . --include="*.json" --include="*.html" --include="*.js" --exclude-dir=.git \
    | grep -v "github.com\|githubusercontent.com\|shields.io\|fonts.googleapis.com\|fonts.gstatic.com\|schema.org" \
    | sort -u

echo ""
if [ "$FOUND_BLOCKER" -eq 1 ]; then
    echo "RESULT: leak-check FAILED - do not commit/push until the items above are redacted."
    exit 1
else
    echo "RESULT: no blockers. Skim the URL list above once, then it's safe to proceed."
    exit 0
fi
