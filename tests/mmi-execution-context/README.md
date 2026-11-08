# CIM callback and cancellation execution context

MMI3 3.0.0-14 omits execution-context capture in its .NET Core callback receiver.
Its cancellation subscription also calls native Cancel directly on the disposing
thread. AsyncLocal values, cultures and managed Windows impersonation can differ
from the subscribing caller. A throwing callback leaves InUserCode set.

Release 15 restores the captured execution context for user callbacks and
cancellation, honors a null capture when flow is deliberately suppressed, resets
InUserCode in finally, and clears disposed subscriptions' operation/context
references. This changes two implementation files and no public API.

The fixture compiles an independent Windows native driver that invokes managed
callbacks on fresh CreateThread workers. It covers ambient values, culture/UI
culture, repeated callbacks, callback mutation, exceptions, suppressed flow,
worker-context restoration, exactly-once cancellation, native cancellation
failure and disposed-subscription reference release. It also runs a real local
asynchronous Win32_OperatingSystem query, with different markers at query
creation, subscription and after subscription, to verify subscription capture.

Impersonation uses a temporary restricted token derived from the current
process: DISABLE_MAX_PRIVILEGE plus an Everyone restricting SID. It creates no
account or credential. WindowsIdentity.RunImpersonated establishes managed
impersonation; the native driver checks the actual worker thread's token. The
original source handle is disposed before invoking the worker, exercising the
captured context's token lifetime. A separate case starts with an impersonating
worker and a normal subscriber, checking restoration in both directions.
These checks do not establish remote/domain authentication or raw Win32-only
impersonation flow. No listener, service or trust-store configuration changes.

The standalone and original PowerShell baseline reproduce 29 context mismatches, eight worker-state
leaks and four stale user-code markers in 147 checks. The corrected fixture has
151 checks, including four extra disposed-reference assertions.

```sh
MINGW_PREFIX=/clang64 bash mingw-w64-dotnet-mmi3/check-execution-context.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash mingw-w64-dotnet-mmi3/check-execution-context.sh NEW_OUTPUT
MINGW_PREFIX=/clang64 bash tests/mmi-execution-context/check-powershell.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/mmi-execution-context/check-powershell.sh NEW_OUTPUT
```

Each output/cache must be new. Restore uses the installed source feed; the
standalone gate checks the archive and implementation bytes. The PowerShell
wrapper runs STA/MTA and verifies the actual bundled MMI against its installed
source archive. Four test-only substitutions expose the entry point and supply
the driver's explicit path. Baseline mode is the standalone wrapper's third
argument after FEED, or the PowerShell wrapper's second argument.

The source audit records 21 zero-fuzz patches, 77 recipe inputs and the two
changed C# files. Full source package/API checks and actual application results
are recorded separately. Complete native/provider compatibility, authenticated
remote CIM/WSMan and the remaining SqlClient/Windows.Compatibility gates remain
open; experimental binaries are not published.

Implementation references: [.NET 8 ExecutionContext](https://github.com/dotnet/runtime/blob/v8.0.0/src/libraries/System.Private.CoreLib/src/System/Threading/ExecutionContext.cs),
[WindowsIdentity](https://github.com/dotnet/runtime/blob/v8.0.0/src/libraries/System.Security.Principal.Windows/src/System/Security/Principal/WindowsIdentity.cs),
[RunImpersonated](https://learn.microsoft.com/en-us/dotnet/api/system.security.principal.windowsidentity.runimpersonated?view=net-8.0),
[CreateRestrictedToken](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-createrestrictedtoken),
and [IsTokenRestricted](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-istokenrestricted).

MMI3 3.0.0-15 and PowerShell 7.4.20-18 passed clean
`makepkg --cleanbuild --force --noconfirm` builds in CLANG64 and UCRT64.
Fresh installed standalone consumers passed 151 checks per environment. The
actual PowerShell bundles passed the same 151 checks in each STA/MTA mode,
including the real local asynchronous query. All reported context mismatches,
worker-state leaks and stale user-code markers are zero. The installed MMI DLLs
match their source archives byte for byte. SDK compilation retained three
CA1846 warnings per environment and one CLANG64 desktop-console NETSDK1106
warning; all compiler invocations reported zero errors.

See [package evidence](package-results-20261109.json),
[PowerShell evidence](powershell-results-20261109.json), and
[temporary build cleanup](cleanup-20261109.json).
