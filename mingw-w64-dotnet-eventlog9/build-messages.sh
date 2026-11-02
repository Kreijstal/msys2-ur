#!/usr/bin/env bash
set -euo pipefail
out=$(cd "${1:?prepared root}" && pwd)
mkdir "$out/messages"
cd "$out/messages"
/usr/bin/windmc -n "$out/r/src/libraries/System.Diagnostics.EventLog/src/Messages/EventLogMessages.mc" > windmc.log 2>&1
cp "$out/r/src/libraries/System.Diagnostics.EventLog/src/Messages/EventLogMessages.rc" EventLogMessages.original.rc
/clang64/bin/windres --preprocessor=/clang64/bin/clang --preprocessor-arg=-E --preprocessor-arg=-xc --preprocessor-arg=-DRC_INVOKED -i EventLogMessages.original.rc -O res -o EventLogMessages.res > windres.log 2>&1
