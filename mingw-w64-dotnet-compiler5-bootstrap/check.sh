#!/usr/bin/env bash
set -euo pipefail
/usr/bin/python3 "$(dirname "$0")/check.py" "$@"
