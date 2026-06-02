# build.ps1 — produce a single-file Windows GUI exe in dist\.
# Requires: pip install pyinstaller
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name "OTBM Item Remapper" `
  --paths src `
  src\gui.py
Write-Host "Built: $PSScriptRoot\dist\OTBM Item Remapper.exe"
