# start-server.ps1
# Sets up a virtual environment, installs all dependencies, and starts the OpenAPI tool server.

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

# ── Resolve venv Python/pip executables directly (avoids PATH issues on Windows) ──
$VenvDir = Join-Path $Root ".venv-win"
$Python  = Join-Path $VenvDir "Scripts\python.exe"
$Pip     = Join-Path $VenvDir "Scripts\pip.exe"

# ── 1. Create venv if it doesn't exist ───────────────────────────────────────
if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment at .venv ..."
    python -m venv $VenvDir
}

# ── 2. Upgrade pip ───────────────────────────────────────────────────────────
Write-Host "Upgrading pip ..."
& $Python -m pip install --upgrade pip --quiet

# ── 3. Install all requirements files ────────────────────────────────────────
$RequirementsFiles = @(
    "src\openapi-tool-server\requirements.txt",
    "src\services\dataObjectQueryService\requirements.txt"
)

foreach ($ReqFile in $RequirementsFiles) {
    $FullPath = Join-Path $Root $ReqFile
    if (Test-Path $FullPath) {
        Write-Host "Installing dependencies from $ReqFile ..."
        & $Pip install -r $FullPath --quiet
    } else {
        Write-Warning "Requirements file not found, skipping: $ReqFile"
    }
}

# ── 4. Start the OpenAPI tool server ─────────────────────────────────────────
Write-Host ""
Write-Host "Starting OpenAPI tool server on http://localhost:8001 ..."
Write-Host "Press Ctrl+C to stop."
Write-Host ""
$ServerScript = Join-Path $Root "src\openapi-tool-server\server.py"
& $Python $ServerScript
