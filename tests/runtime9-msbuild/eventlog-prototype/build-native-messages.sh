#!/usr/bin/env bash
set -euo pipefail
root=$(cd "${1:?root}" && pwd)
mkdir "$root/messages-build3"
cd "$root/messages-build3"
/usr/bin/windmc -n "$root/r/src/libraries/System.Diagnostics.EventLog/src/Messages/EventLogMessages.mc" > windmc.log 2>&1
cp "$root/r/src/libraries/System.Diagnostics.EventLog/src/Messages/EventLogMessages.rc" EventLogMessages.original.rc
/clang64/bin/windres --preprocessor=/clang64/bin/clang --preprocessor-arg=-E --preprocessor-arg=-xc --preprocessor-arg=-DRC_INVOKED -i EventLogMessages.original.rc -O res -o EventLogMessages.res > windres.log 2>&1
ls -l
