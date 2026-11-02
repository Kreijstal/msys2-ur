#!/usr/bin/env bash
set -euo pipefail
illink_prefix=$(cd "$(dirname "$0")/.." && pwd)
exec "$illink_prefix/lib/dotnet/dotnet.exe" "$illink_prefix/lib/dotnet/tool-packs/illink-10.0.5-bootstrap/illink.dll" "$@"
