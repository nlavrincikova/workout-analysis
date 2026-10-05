# check-leaks.ps1 - run manually before staging (git add) and again right before
# git push. Doesn't fix anything, doesn't commit or push anything itself -
# it just scans working files and tells you what's about to go public.
#
# Two kinds of check:
#   1. Generic patterns (this file) - need no secrets, safe to publish with the repo.
#   2. Private literals - the real host and webhook IDs live in ~/.leak-patterns, one per
#      line, and NEVER in this repo: this script is public, so it must not contain them.
#      Override the location with the LEAK_PATTERNS_FILE environment variable.

$blocked = $false
$notGit = '\\\.git\\'
# Scripts are in scope on purpose: a checker that can't see its own file is how a secret ends up inside it.
$scanFiles = Get-ChildItem -Recurse -Include *.json, *.html, *.js, *.md, *.py, *.sh, *.ps1 -File |
    Where-Object { $_.FullName -notmatch $notGit }
$jsonFiles = $scanFiles | Where-Object { $_.Extension -eq '.json' }
$urlFiles = $scanFiles | Where-Object { $_.Extension -in '.json', '.html', '.js' }

$patternFile = if ($env:LEAK_PATTERNS_FILE) { $env:LEAK_PATTERNS_FILE } else { Join-Path $env:USERPROFILE '.leak-patterns' }

Write-Host "== Checking for private literals (live host, real webhook IDs) =="
if (Test-Path $patternFile) {
    $literals = @(Get-Content $patternFile | Where-Object { $_.Trim() -and ($_ -notmatch '^\s*#') })
    $privateHits = @()
    if ($literals.Count -gt 0) { $privateHits = @($scanFiles | Select-String -SimpleMatch -Pattern $literals) }
    if ($privateHits.Count -gt 0) {
        $privateHits | ForEach-Object { Write-Host "$($_.Path):$($_.LineNumber): $($_.Line)" }
        Write-Host "BLOCKED: a private literal from $patternFile was found above. Redact before committing/pushing."
        $blocked = $true
    } else {
        Write-Host "OK - none of the private literals found."
    }
} else {
    Write-Host "WARNING: $patternFile not found - the live host and real webhook IDs were NOT checked (the generic checks below still ran)."
}

Write-Host ""
Write-Host "== Checking for unredacted webhook IDs (any value other than the placeholder) =="
$webhookHits = @()
$webhookHits += $jsonFiles | Select-String -Pattern '"webhookId"\s*:\s*"' |
    Where-Object { $_.Line -notmatch 'REDACTED-REGENERATED-ON-IMPORT' }
$webhookHits += $scanFiles | Select-String -Pattern '(?i)webhook(-test)?/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
if ($webhookHits.Count -gt 0) {
    $webhookHits | ForEach-Object { Write-Host "$($_.Path):$($_.LineNumber): $($_.Line)" }
    Write-Host "BLOCKED: unredacted webhook ID found above. Replace it with the REDACTED-REGENERATED-ON-IMPORT / YOUR-...-WEBHOOK-ID placeholder."
    $blocked = $true
} else {
    Write-Host "OK - no unredacted webhook IDs found."
}

Write-Host ""
Write-Host "== All other embedded URLs found (review by eye - most of these are fine) =="
$excludePattern = 'github\.com|githubusercontent\.com|shields\.io|fonts\.googleapis\.com|fonts\.gstatic\.com|schema\.org'
$urls = $urlFiles |
    Select-String -Pattern 'https?://[^"''\s]+' -AllMatches |
    ForEach-Object { $_.Matches.Value } |
    Where-Object { $_ -notmatch $excludePattern } |
    Sort-Object -Unique
$urls | ForEach-Object { Write-Host $_ }

Write-Host ""
if ($blocked) {
    Write-Host "RESULT: leak-check FAILED - do not commit/push until the items above are redacted."
    exit 1
} else {
    Write-Host "RESULT: no blockers. Skim the URL list above once, then it's safe to proceed."
    exit 0
}
