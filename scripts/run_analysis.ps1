# Windows PowerShell version of run_analysis.sh
#   $env:SONAR_HOST_URL = "http://localhost:9000"
#   $env:SONAR_TOKEN    = "<token>"
#   .\scripts\run_analysis.ps1                                   # first analysis
#   $env:IMPROVE = "1"; $env:VERSION = "1.1"; .\scripts\run_analysis.ps1   # second analysis
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not $env:SONAR_HOST_URL) { $env:SONAR_HOST_URL = "http://localhost:9000" }
if (-not $env:SONAR_TOKEN)    { throw "Set `$env:SONAR_TOKEN first" }
$version = if ($env:VERSION) { $env:VERSION } else { "1.0" }
$wait = if ($env:WAIT -eq "1") { "-Dsonar.qualitygate.wait=true" } else { "" }

New-Item -ItemType Directory -Force reports | Out-Null

Write-Host "== tests + coverage for the ShopFlow app"
python -m pytest -q -o junit_family=xunit1 --junitxml=reports/junit.xml --cov --cov-config=.coveragerc --cov-report=xml:reports/coverage.xml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== tests + coverage for sonar_tools"
$env:COVERAGE_FILE = ".coverage_tools"
python -m pytest -q --cov --cov-config=coveragerc_tools.ini --cov-report=xml:reports/coverage_tools.xml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Remove-Item Env:COVERAGE_FILE

Write-Host "== sonar-scanner: shopflow-eval (version $version)"
sonar-scanner "-Dsonar.projectVersion=$version" $wait

if ($env:SKIP_TOOLS -ne "1") {
    Write-Host "== sonar-scanner: sonar-tools-eval"
    sonar-scanner "-Dproject.settings=sonar-project.sonar_tools.properties" "-Dsonar.projectVersion=$version" $wait
}
Write-Host "Done. Open $($env:SONAR_HOST_URL)/dashboard?id=shopflow-eval"
