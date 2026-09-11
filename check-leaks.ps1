# check-leaks.ps1 - run manually before staging (git add) and again right before
# git push. Doesn't fix anything, doesn't commit or push anything itself -
# it just scans working files and tells you what's about to go public.

Write-Host "== Checking for the live n8n production host =="
$files = Get-ChildItem -Recurse -Include *.json, *.html, *.js -File |
    Where-Object { $_.FullName -notmatch '\\\.git\\' }

$hostHits = $files | Select-String -Pattern 'nn\.ehomedn\.cc'
$blocked = $false
if ($hostHits) {
    $hostHits | ForEach-Object { Write-Host "$($_.Path):$($_.LineNumber): $($_.Line)" }
    Write-Host "BLOCKED: live production host found above. Redact before committing/pushing."
    $blocked = $true
} else {
    Write-Host "OK - no live host found."
}

Write-Host ""
Write-Host "== All other embedded URLs found (review by eye - most of these are fine) =="
$excludePattern = 'github\.com|githubusercontent\.com|shields\.io|fonts\.googleapis\.com|fonts\.gstatic\.com|schema\.org'
$urls = $files |
    Select-String -Pattern 'https?://[^"''\s]+' -AllMatches |
    ForEach-Object { $_.Matches.Value } |
    Where-Object { $_ -notmatch $excludePattern } |
    Sort-Object -Unique
$urls | ForEach-Object { Write-Host $_ }

Write-Host ""
if ($blocked) {
    Write-Host "RESULT: leak-check FAILED - do not commit/push until the host above is redacted."
    exit 1
} else {
    Write-Host "RESULT: no blockers. Skim the URL list above once, then it's safe to proceed."
    exit 0
}
