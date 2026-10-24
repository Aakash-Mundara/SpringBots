#!/usr/bin/env sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if command -v mvn >/dev/null 2>&1; then exec mvn -f "$ROOT/backend/pom.xml" "$@"; fi
MVN_VERSION=3.9.11
CACHE="${HOME}/.cache/onboardiq/apache-maven-${MVN_VERSION}"
if [ ! -x "$CACHE/bin/mvn" ]; then
  mkdir -p "$(dirname "$CACHE")"
  ARCHIVE="${TMPDIR:-/tmp}/apache-maven-${MVN_VERSION}-bin.tar.gz"
  echo "Maven not installed; downloading Apache Maven ${MVN_VERSION} (first run only)..."
  if command -v curl >/dev/null 2>&1; then curl -fL "https://archive.apache.org/dist/maven/maven-3/${MVN_VERSION}/binaries/apache-maven-${MVN_VERSION}-bin.tar.gz" -o "$ARCHIVE"; else echo "Install Maven 3.9+ or curl." >&2; exit 1; fi
  tar -xzf "$ARCHIVE" -C "$(dirname "$CACHE")"
fi
exec "$CACHE/bin/mvn" -f "$ROOT/backend/pom.xml" "$@"
