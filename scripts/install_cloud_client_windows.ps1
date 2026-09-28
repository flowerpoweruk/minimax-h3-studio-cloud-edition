$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

Write-Host "Minimax H3 Studio - Cloud Edition" -ForegroundColor Cyan
Write-Host "Windows cloud-client installer (no local GPU required)" -ForegroundColor Cyan

if (-not (Get-Command uv.exe -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "Windows Package Manager (winget) is required to install uv automatically. Install App Installer from Microsoft, then run this file again."
    }
    Write-Host "Installing uv..."
    winget install --id astral-sh.uv --exact --silent --accept-package-agreements --accept-source-agreements
    $env:Path += ";$env:USERPROFILE\.local\bin;$env:LOCALAPPDATA\Programs\uv"
}

if (-not (Get-Command uv.exe -ErrorAction SilentlyContinue)) {
    throw "uv was installed but is not available in this terminal. Close this window and run the installer again."
}

Write-Host "Installing Python 3.10..."
uv python install 3.10
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Venv = Join-Path $ProjectRoot "app\env"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
Write-Host "Creating the Cloud Edition environment..."
uv venv $Venv --python 3.10 --allow-existing
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Installing the Studio client..."
uv pip install --python $VenvPython -r (Join-Path $ProjectRoot "studio\requirements.txt")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$SettingsDir = Join-Path $ProjectRoot "studio\data"
$SettingsFile = Join-Path $SettingsDir "runpod_settings.json"
New-Item -ItemType Directory -Path $SettingsDir -Force | Out-Null

$Settings = [ordered]@{ provider = "runpod" }
if (Test-Path -LiteralPath $SettingsFile) {
    try {
        $Existing = Get-Content -Raw -LiteralPath $SettingsFile | ConvertFrom-Json
        $Existing | Add-Member -NotePropertyName provider -NotePropertyValue "runpod" -Force
        $Settings = $Existing
    } catch {
        Write-Warning "The previous Runpod settings file was unreadable and has been replaced."
    }
}
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $SettingsFile,
    ($Settings | ConvertTo-Json -Depth 10),
    $Utf8NoBom
)

Write-Host ""
Write-Host "Cloud client installed successfully." -ForegroundColor Green
Write-Host "No NVIDIA GPU, CUDA toolkit, ComfyUI, or H3 model download was required on this PC."
Write-Host "Next: double-click run-cloud-edition.bat, then add your Runpod API key in Settings."
