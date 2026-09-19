<#
  publish.ps1 -- one command to ship this skill.

  Steps:
    1. commit (only if the working tree is dirty; needs -Message)
    2. push origin main
    3. rebuild the distribution zip from git (git archive HEAD), so the zip
       always matches the repo instead of whatever happens to be in the folder
    4. optional: cut a GitHub release with the zip attached (needs -Version)

  Usage:
    .\tools\publish.ps1 -Message "fix: ..."
    .\tools\publish.ps1 -Message "feat: ..." -Version v1.1.0
    .\tools\publish.ps1 -Message "feat: ..." -Version v1.1.0 -Notes "what changed"

  Notes:
    * gh must be on PATH for step 4 (winget install GitHub.cli).
    * The zip is written next to the skill folder, NOT inside the repo, so
      building it never dirties the working tree.
#>
[CmdletBinding()]
param(
    [string]$Message,
    [string]$Version,
    [string]$Notes
)

$ErrorActionPreference = 'Stop'

$skillDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$zipName  = Split-Path $skillDir -Leaf            # e.g. wechat-extract-skill
$zipPath  = Join-Path (Split-Path $skillDir -Parent) ($zipName + '.zip')

Write-Host "skill dir : $skillDir"
Write-Host "zip path  : $zipPath"
Write-Host ""

# 1) commit -------------------------------------------------------------
$dirty = & git -C $skillDir status --porcelain
if ($dirty) {
    if (-not $Message) {
        throw "Working tree has changes but -Message was not given. Nothing was committed."
    }
    Write-Host "[1/4] committing..."
    & git -C $skillDir add -A
    & git -C $skillDir commit -m $Message
    if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
} else {
    Write-Host "[1/4] working tree clean - nothing to commit"
}

# 2) push ---------------------------------------------------------------
Write-Host "[2/4] pushing..."
& git -C $skillDir push origin main
if ($LASTEXITCODE -ne 0) { throw "git push failed" }

# 3) rebuild the zip from git -------------------------------------------
Write-Host "[3/4] rebuilding $zipName.zip from HEAD..."
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
& git -C $skillDir archive --format=zip --prefix="$zipName/" -o $zipPath HEAD
if ($LASTEXITCODE -ne 0) { throw "git archive failed" }

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
$fileCount = ($zip.Entries | Where-Object { -not $_.FullName.EndsWith('/') }).Count
$zip.Dispose()
$sizeKb = [math]::Round((Get-Item $zipPath).Length / 1KB, 1)
Write-Host "      $fileCount files, $sizeKb KB"
if ($fileCount -lt 10) { throw "zip looks wrong ($fileCount files) - refusing to continue" }

# 4) release ------------------------------------------------------------
if ($Version) {
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) { throw "gh not found on PATH; install it (winget install GitHub.cli) or skip -Version" }
    Write-Host "[4/4] creating release $Version..."
    $ghArgs = @('release', 'create', $Version, $zipPath, '--title', $Version)
    if ($Notes) { $ghArgs += @('--notes', $Notes) } else { $ghArgs += @('--generate-notes') }
    & $gh.Source @ghArgs
    if ($LASTEXITCODE -ne 0) { throw "gh release create failed" }
} else {
    Write-Host "[4/4] skipped (no -Version given)"
}

Write-Host ""
Write-Host "done. HEAD: $((& git -C $skillDir rev-parse --short HEAD))"
