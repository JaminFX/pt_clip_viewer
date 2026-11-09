$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
py -3.14 -m venv .venv-build
if ($LASTEXITCODE -ne 0) { throw 'Python 3.14 is required.' }
$python = Join-Path $PSScriptRoot '.venv-build\Scripts\python.exe'
& $python -m pip install --require-hashes -r requirements-build.lock
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $python build_app.py
if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }
$iscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
if (-not (Test-Path -LiteralPath $iscc)) {
    $iscc = (Get-Command ISCC.exe -ErrorAction Stop).Source
}
& $iscc installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
Write-Host "Installer created in $PSScriptRoot\release"
