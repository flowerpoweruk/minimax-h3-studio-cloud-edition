$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

Write-Host "Minimax H3 Studio - Cloud Edition" -ForegroundColor Cyan
Write-Host "Windows CUDA one-click installer" -ForegroundColor Cyan

if (-not (Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue)) {
    throw "An NVIDIA driver with CUDA support is required. Install the current NVIDIA driver first."
}

if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Git..."
    winget install --id Git.Git --exact --silent --accept-package-agreements --accept-source-agreements
    $env:Path += ";$env:ProgramFiles\Git\cmd"
}

if (-not (Get-Command uv.exe -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    winget install --id astral-sh.uv --exact --silent --accept-package-agreements --accept-source-agreements
    $env:Path += ";$env:USERPROFILE\.local\bin;$env:LOCALAPPDATA\Programs\uv"
}

if (-not (Get-Command uv.exe -ErrorAction SilentlyContinue)) {
    throw "uv was installed but is not available in this terminal. Close this window and run the installer again."
}

uv python install 3.10
$Python = (uv python find 3.10).Trim()
if (-not $Python) { throw "Python 3.10 could not be installed." }

& $Python "$PSScriptRoot\install_windows_cuda.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
