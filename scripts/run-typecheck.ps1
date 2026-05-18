#!/usr/bin/env pwsh
# Run basedpyright type checker
Set-Location (Join-Path $PSScriptRoot "..\src\vigilancia_multiagente")
python -m basedpyright @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
