# Synchronous CIM result ownership

MMI3 3.0.0-16 wraps operation-owned indications directly when
ShortenLifetimeOfResults is enabled. Disposing the managed result then deletes
the provider's instance. Its synchronous result paths also abandon borrowed
instance/completion-details pointer cells and can lose a newly cloned result
when MoveNext fails before transferring it to Current.

Release 17 always clones borrowed indications, releases borrowed wrapper cells
without deleting the native result, rolls back wrappers on retrieval/callback
failure, and disposes untransferred results on MoveNext failure. Existing
shortened versus caller-owned managed lifetimes and instance session metadata
are preserved. Only five C# implementation files change; all 152 inputs remain.
The public/protected API remains 512 declarations.

The C/mi.h peer supplies independent instance, class and error objects with
clone/delete counters. The fixture uses the actual managed synchronous
enumerators and MoveNext, including native operation disposal. Across all three
result kinds and both lifetime modes it covers success, clone failure, function
failure, operation failure, null result, started notification and callback error.
The production suite has 409 assertions. The old installed baseline reproduces
one provider-source deletion in 15 control assertions, including original
PowerShell STA and MTA runs.

A private diagnostic hook records wrapper objects immediately after their
HGlobal allocation. The fixture then inspects allocatedData after the normal
cleanup paths. Keeping the wrappers reachable deliberately excludes deferred
finalization as a substitute for explicit disposal. The old two-case baseline
leaves three of seven wrapper allocations unreleased; the fixed 42-case run
releases all 198 allocations and passes 452 assertions. Borrowed MI_Class cells
already had a finalizer in release 16; the new change makes their cleanup
deterministic. MI_Instance cells had no such fallback.

The hook changes only a separate diagnostic MI_NativeObject.cs. Its patch and
source hashes are retained as evidence; diagnostic DLLs/packages are not installed
or published. The production source and package audit reject this hook.

```sh
MINGW_PREFIX=/clang64 bash mingw-w64-dotnet-mmi3/check-sync-results.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash mingw-w64-dotnet-mmi3/check-sync-results.sh NEW_OUTPUT
MINGW_PREFIX=/clang64 bash tests/mmi-sync-results/check-powershell.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/mmi-sync-results/check-powershell.sh NEW_OUTPUT
```

Standalone optional arguments are FEED followed by --baseline. The PowerShell
wrapper accepts --baseline after OUTPUT and verifies the actual bundled MMI
against the installed source archive before STA/MTA execution. Output/cache
paths must be fresh. --trace-wrappers is accepted only with the separately
prepared private diagnostic build; it is not a production package mode.

Microsoft's [native indication contract](https://github.com/MicrosoftDocs/sdk-api/blob/docs/sdk-api-src/content/mi/nf-mi-mi_operation_getindication.md)
and [instance retrieval contract](https://learn.microsoft.com/en-us/windows/win32/api/mi/nf-mi-mi_operation_getinstance)
give results and completion details an operation-bound lifetime; retaining them
requires cloning. This fixture does not establish authenticated remote
CIM/WSMan, all provider behavior or the remaining SqlClient/Windows.Compatibility
gates. Experimental binaries remain held from publication.

A separate [late-discard diagnostic](late-discard-results-20261109.json) records
an internal callback failure during Clone, after native retrieval but before
MoveNext transfers Current. All six type/lifetime cases delete their untransferred
clone before propagating the original error. It passes 67 assertions and releases
all 24 tracked wrapper allocations. This uses the same private tracing build;
its extra peer hook and fixture source remain diagnostic-only evidence.

MMI3 3.0.0-17 and PowerShell 7.4.20-23 pass clean
`makepkg --cleanbuild --force --noconfirm` builds in CLANG64 and UCRT64.
Fresh installed consumers and each original PowerShell STA/MTA mode pass all
409 production assertions with zero defects. The bundled MMI DLLs exactly match
the installed source archives. All compiler invocations report zero errors;
existing warnings remain three SDK CA1846 per environment and one CLANG64
desktop-console NETSDK1106 warning. WinRM remains Stopped/Manual.

See [package results](package-results-20261109.json),
[PowerShell results](powershell-results-20261109.json),
[remote source identities](remote-input-identity-20261109.json), and
[temporary build cleanup](cleanup-20261109.json).
