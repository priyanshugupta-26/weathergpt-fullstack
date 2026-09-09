Set-Location $PSScriptRoot
py -3 scripts\launch.py
if ($LASTEXITCODE -ne 0) { Read-Host 'Press Enter to close' }
