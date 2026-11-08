#!/usr/bin/env bash
# Run unit tests with coverage, then analyse BOTH projects with sonar-scanner.
#
#   export SONAR_HOST_URL=http://localhost:9000
#   export SONAR_TOKEN=<token>            # My Account > Security > Generate Tokens
#   scripts/run_analysis.sh               # first analysis (version 1.0)
#   IMPROVE=1 VERSION=1.1 scripts/run_analysis.sh   # second analysis -> trends / new code
#
# Optional: SKIP_TOOLS=1 skips the sonar_tools project; WAIT=1 fails when the gate fails.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${SONAR_HOST_URL:=http://localhost:9000}"
: "${SONAR_TOKEN:?Set SONAR_TOKEN first}"
VERSION="${VERSION:-1.0}"
WAIT_ARG=""
[ "${WAIT:-0}" = "1" ] && WAIT_ARG="-Dsonar.qualitygate.wait=true"
export SONAR_HOST_URL SONAR_TOKEN

mkdir -p reports

echo "== tests + coverage for the ShopFlow app"
python -m pytest -q -o junit_family=xunit1 --junitxml=reports/junit.xml \
  --cov --cov-config=.coveragerc --cov-report=xml:reports/coverage.xml

echo "== tests + coverage for sonar_tools"
COVERAGE_FILE=.coverage_tools python -m pytest -q \
  --cov --cov-config=coveragerc_tools.ini --cov-report=xml:reports/coverage_tools.xml

echo "== sonar-scanner: shopflow-eval (version $VERSION)"
sonar-scanner -Dsonar.projectVersion="$VERSION" $WAIT_ARG

if [ "${SKIP_TOOLS:-0}" != "1" ]; then
  echo "== sonar-scanner: sonar-tools-eval"
  sonar-scanner -Dproject.settings=sonar-project.sonar_tools.properties \
    -Dsonar.projectVersion="$VERSION" $WAIT_ARG
fi

echo "Done. Open $SONAR_HOST_URL/dashboard?id=shopflow-eval"
