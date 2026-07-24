#!/usr/bin/env sh
set -eu

if ! command -v mvn >/dev/null 2>&1; then
  echo "Maven is required to run this demo wrapper." >&2
  exit 127
fi

exec mvn "$@"
