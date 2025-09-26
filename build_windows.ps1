<#
.SYNOPSIS
  Build a Windows executable for the Sakana Desktop Assistant using PyInstaller.

.DESCRIPTION
  - Ensures PyInstaller is installed in the current Python environment
  - Builds a single-file executable from src\main.py
  - Places the built EXE under .\dist\
  - Optionally runs the EXE after a successful build

.PARAMETER RunAfterBuild
  If provided, the script will run the built executable after a successful build.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
  powershell -ExecutionPolicy Bypass -File .\build_windows.ps1 -RunAfterBuild

.NOTES
  - This script should be executed from the project root directory.
  - If your project requires additional data files at runtime, add them using
    the --add-data option below (Windows format uses semicolon ';' as separator).
#>

param(
  [switch] $RunAfterBuild
)

$ErrorActionPreference = 'Stop'

# Move to the project root (directory where this script resides)
Set-Location -Path $PSScriptRoot

Write-Host "==> Checking Python..." -ForegroundColor Cyan
$pythonVersion = & python --version 2>$null
if (-not $pythonVersion) {
  Write-Error "Python is not available on PATH. Please install Python and try again."
}
Write-Host "Using $pythonVersion" -ForegroundColor Green

Write-Host "==> Ensuring PyInstaller is installed..." -ForegroundColor Cyan
$pyinstallerOk = & python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
  & python -m pip install --upgrade pip
  & python -m pip install pyinstaller
}

# Clean previous builds
Write-Host "==> Cleaning previous build artifacts..." -ForegroundColor Cyan
if (Test-Path .\build) { Remove-Item -Recurse -Force .\build }
if (Test-Path .\dist) { Remove-Item -Recurse -Force .\dist }

# Prepare PyInstaller arguments
$exeName = "sakana-assistant"
$entry   = "src\main.py"

if (-not (Test-Path $entry)) {
  Write-Error "Entry file '$entry' not found. Ensure you are in the project root."
}

# Optionally include a default config if present
$addDataArgs = @()
if (Test-Path .\config.yaml) {
  # On Windows, add-data uses the syntax: SRC;DEST
  $addDataArgs += @('--add-data', "config.yaml;.")
}

# Ensure the 'src' package is on the analysis path
$pathsArgs = @('--paths', '.', '--paths', 'src')

# Common build args
$commonArgs = @(
  '--noconfirm',
  '--clean',
  '--onefile',
  '--name', $exeName
) + $addDataArgs + $pathsArgs

Write-Host "==> Building $exeName using PyInstaller..." -ForegroundColor Cyan
& python -m PyInstaller @commonArgs $entry

if ($LASTEXITCODE -ne 0) {
  Write-Error "Build failed with exit code $LASTEXITCODE"
}

$builtExe = Join-Path -Path (Resolve-Path .\dist) -ChildPath ("$exeName.exe")
if (-not (Test-Path $builtExe)) {
  Write-Error "Build completed but executable not found at $builtExe"
}

Write-Host "==> Build succeeded: $builtExe" -ForegroundColor Green

if ($RunAfterBuild) {
  Write-Host "==> Running $exeName... (Press Ctrl+C to exit)" -ForegroundColor Cyan
  & $builtExe
}