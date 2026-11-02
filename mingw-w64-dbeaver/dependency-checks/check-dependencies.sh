#!/usr/bin/env bash
set -euo pipefail
source "${MINGW_PREFIX}/share/java-build-helper/javabuild.sh"
_check_root=${1:-$PWD}
mkdir -p checks
mapfile -t _roots < "$_check_root/check-roots.txt"
_cp=$(jb_cp "${_roots[@]}")
javac --release 21 -encoding UTF-8 -d "$(jb_w checks)" -cp "$_cp" "$(jb_w "$_check_root/DependencyChecks.java")"
java -Djava.awt.headless=true -cp "$(jb_w checks);$_cp" DependencyChecks
_osgi=$(ls "$JB_PLUGINS"/org.eclipse.osgi_*.jar | head -1)
javac --release 21 -d "$(jb_w checks)" -cp "$_cp;$(jb_w "$_osgi")" "$(jb_w "$_check_root/OsgiChecks.java")" "$(jb_w "$_check_root/RunOsgiChecks.java")"
jar --create --file "$(jb_w osgi-checks.jar)" --manifest "$(jb_w "$_check_root/checks.MF")" -C "$(jb_w checks)" OsgiChecks.class
java -Djava.awt.headless=true -cp "$(jb_w checks);$(jb_w "$_osgi")" RunOsgiChecks "$(jb_w "$JB_PLUGINS")" "$(jb_w "$PWD/osgi-check-store")" "$(jb_w "$PWD/osgi-checks.jar")"
