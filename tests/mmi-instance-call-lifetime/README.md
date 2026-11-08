# Native instance lifetime during property-count reads

The installed MMI3 3.0.0-11 package can delete a transient CimInstance while its
native GetElementCount call is still running. With optimized JIT compilation,
`MakeInstance().CimInstanceProperties.Count` no longer keeps the managed owner
live after extracting the native handle. A collection during the native call
runs the owner's finalizer before that call returns.

The owned C/mi.h driver forces collection inside GetElementCount, records native
deletion and returns INVALID_PARAMETER if the instance was deleted mid-call.
It retains its static storage until process exit, so the baseline observes the
failure without dereferencing freed storage. Four property descriptor reads
(name, type, flags and value) provide existing-path controls. Each instance must
be deleted exactly once after its call finishes. This fixture does not test
remote authentication or provider-wide races.

Release 12 adds a finally block with GC.KeepAlive on the owning CimInstance
around the property-count call and result handling. It changes no public API.

```sh
MINGW_PREFIX=/clang64 bash mingw-w64-dotnet-mmi3/check-instance-call-lifetime.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash mingw-w64-dotnet-mmi3/check-instance-call-lifetime.sh NEW_OUTPUT
```

The fixture uses the installed source-only feed, a fresh package cache, exact
archive/DLL byte checks and DOTNET_TieredCompilation=0. For a known affected
source package, pass its feed as the second argument and `--baseline` as the
third. Baseline mode must reproduce at least one early-deletion error.

The source audit records all 18 zero-fuzz patch replays and all 65 recipe source
checksums. Comparison against release 11 proves that the property-count method
is the only changed compiled C# input. Full package checks and the 512-entry
public API gate remain required. MMI remains experimental until the broader
native and authenticated remote integration requirements are satisfied.

The application wrapper builds the same C# fixture as a signed friend library,
exposes its entry point and supplies the native driver's explicit path. It checks
the actual bundled MMI against the installed source archive and runs STA and MTA:

```sh
MINGW_PREFIX=/clang64 bash tests/mmi-instance-call-lifetime/check-powershell.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/mmi-instance-call-lifetime/check-powershell.sh NEW_OUTPUT
```

Pass `--baseline` as the second argument only when the installed PowerShell
bundle and installed source feed both contain the affected implementation.
Recorded baseline PowerShell 7.4.20-14 reproduces one early deletion in each mode.
Package and application results are stored separately; their recorded exit codes
and source hashes determine validation status.

The recorded release-12 clean package builds and installed checks passed in both
environments. PowerShell 7.4.20-15 also passed clean package builds and the same
five optimized reads in each STA/MTA mode in both environments. See
[package results](package-results-20261108.json) and
[application results](powershell-results-20261108.json) for exact commands,
source/archive/bundle hashes and compiler warning counts. Binary publication
remains disabled while the incomplete dependency gates remain open.
