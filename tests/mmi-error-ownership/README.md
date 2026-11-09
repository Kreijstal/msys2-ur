# CIM exception error-data ownership

MMI3 3.0.0-15 can delete a caller/provider-owned error while computing the
exception message. If Message is missing, NULL, empty or a non-string, a dormant
native-error conversion fallback reads the same error again and deletes it.
The constructor then tries to clone the cleared handle and throws
ArgumentNullException, losing the intended CIM exception and ErrorData.
An empty native error-details wrapper also incorrectly reaches Clone.

Release 16 removes the redundant conversion retry and deletion, retaining the
existing error-code message fallback. Only the temporary message clone and the
exception's independent ErrorData clone are owned by exception construction.
An empty native wrapper is treated as absent details. No public API changes.

The independent C/mi.h driver retains deleted memory until reset so failures
can be observed without dereferencing freed storage. Clone/delete counters
check both public and internal constructors with five Message representations.
The installed baseline reproduces eight source deletions plus one empty-details
failure. The final fixture also checks independent ErrorData after source
disposal, source usability after exception disposal, idempotent cleanup and
exactly-once clone deletion. It creates no repository instances or services.

```sh
MINGW_PREFIX=/clang64 bash mingw-w64-dotnet-mmi3/check-error-ownership.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash mingw-w64-dotnet-mmi3/check-error-ownership.sh NEW_OUTPUT
MINGW_PREFIX=/clang64 bash tests/mmi-error-ownership/check-powershell.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/mmi-error-ownership/check-powershell.sh NEW_OUTPUT
```

The standalone optional arguments are FEED and --baseline. The PowerShell
wrapper accepts --baseline after OUTPUT and checks the actual bundled MMI bytes
against the installed source archive before running STA and MTA. Each cache and
output must be fresh. Test assemblies use an existing signed friend identity;
they are fixtures and are not packaged in PowerShell.

Early fixture iterations added MI_Instance.GetElementAt, which property values
require after name lookup, and corrected the expected managed failure type.
Those failed harness logs are retained separately from the final baseline.
The initial candidate passed 82 assertions; the expanded final fixture adds ten
checks for independent source/error-data disposal, for 92 assertions.
Authenticated remote CIM/WSMan, broader provider behavior and the remaining
SqlClient/Windows.Compatibility gates remain open. Experimental binaries are held.

Microsoft's [MI_Operation_GetInstance contract](https://learn.microsoft.com/en-us/windows/win32/api/mi/nf-mi-mi_operation_getinstance)
also describes completion details as operation-owned results whose lifetime ends
at the next retrieval or operation close; retaining them requires cloning.
This supports preserving the borrowed handle during exception construction.

A separate [synchronous ownership review](native-sync-review-20261109.json)
reproduces another unresolved defect in release 16: shortened synchronous
indication results delete the operation-owned instance without cloning it.
The normal-lifetime control creates/deletes one clone and preserves the source;
the shortened path deletes the source and creates no clone. The independent
probe source and output are retained in evidence. This is a follow-up requirement,
separate from the 92 passing exception-ownership assertions above.

The follow-up probe can be reproduced with
`MINGW_PREFIX=/clang64 bash tests/mmi-error-ownership/evidence-20261109/sync-probe-source/check.sh NEW_OUTPUT`.
Success means that its normal control passes and the shortened-lifetime defect
is reproduced; this diagnostic is intentionally distinct from a passing fixed gate.

MMI3 3.0.0-16 and PowerShell 7.4.20-22 clean
`makepkg --cleanbuild --force --noconfirm` builds pass in CLANG64 and UCRT64.
Fresh standalone consumers and each installed PowerShell STA/MTA mode pass 92
assertions with zero defects. All 512 public/protected declarations remain intact.
Compiler invocations report zero errors; the existing three SDK CA1846 warnings
per environment and one CLANG64 desktop-console NETSDK1106 warning remain.

See [package results](package-results-20261109.json),
[PowerShell results](powershell-results-20261109.json),
[remote input identities](remote-input-identity-20261109.json), and
[temporary build cleanup](cleanup-20261109.json).

The shortened synchronous-result defect and explicit wrapper cleanup are addressed
by [MMI3 release 17](../mmi-sync-results/README.md). The release-16 reproduction
above is retained as historical evidence.
