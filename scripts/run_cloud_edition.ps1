$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot "app\env\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Cloud Edition is not installed. Run install-cloud-client-windows.bat for Runpod, or install-windows-cuda.bat for local CUDA."
}
Set-Location -LiteralPath $ProjectRoot
& $Python "$PSScriptRoot\launch_cloud_edition.py"
exit $LASTEXITCODE
