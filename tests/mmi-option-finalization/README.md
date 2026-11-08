# Native option ownership, finalization and clone rollback

MMI3 3.0.0-13 reclaims option wrappers on explicit disposal, but abandoning a
session or operation option leaves both its native contents and unmanaged
wrapper allocated. A completed operation clone is also hidden in an unevaluated
Lazy: immediate Dispose cannot see the already-created native object.

Release 14 gives successful destination/operation factory and clone results an
internal native owner. Finalization and explicit disposal delete owned native
contents once and release the wrapper allocation. Borrowed wrappers release only
their pointer cells. Failed factory/clone calls clear their outputs and release
wrapper allocations; a timeout-copy failure after a successful operation clone
rolls back that new clone while preserving its source. Operation constructors
publish completed clones to their Lazy immediately, making Dispose effective
before any property is read.

The managed ownership state lives outside native MI layouts. Native calls keep
option handles alive until they return, including application NewSession and
the twelve session operation-start methods that accept options. Generic borrowed
MI_Value results retain their native option owner until conversion/disposal.
MOF calls already had the required KeepAlive protection.

The counted C/mi.h peer uses its own application/options/session function tables.
It records creation/deletion, injects factory and clone failures, forces
compacting GC inside native calls, and retains storage until process exit so
premature deletion can be observed without accessing freed memory. It covers:

- Abandoned native wrappers and public session/operation owners.
- Abandoned clones, borrowed wrappers and retained borrowed Unicode values.
- Explicit and repeated disposal, with independent native deletion counts.
- Reentrant GC during option calls, NewSession and QueryInstances.
- Failed clones/factories, post-clone timeout-copy rollback and immediate public
  operation-clone disposal before its Lazy is otherwise evaluated.

The final fixture has 85 checks on the corrected implementation. Baseline mode
has 79 checks and reproduces 14 abandoned-wrapper leaks, including two borrowed
pointer-cell leaks, plus the immediate-clone disposal defect. Baseline-only
cleanup reclaims its owned test allocations after recording the defect.

A separate control uses actual Windows MI objects for base session, WSMan, DCOM
and operation options, both original and cloned. It checks public-owner collection
and native-wrapper cleanup, plus immediate clone disposal, in 17 checks. The
PowerShell 7.4.20-16 baseline reproduces eight retained real wrappers and a retained
immediately-disposed clone in both STA/MTA modes.

```sh
MINGW_PREFIX=/clang64 bash mingw-w64-dotnet-mmi3/check-option-finalization.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash mingw-w64-dotnet-mmi3/check-option-finalization.sh NEW_OUTPUT
MINGW_PREFIX=/clang64 bash tests/mmi-option-finalization/check-powershell.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/mmi-option-finalization/check-powershell.sh NEW_OUTPUT
```

The standalone wrapper uses a new output/cache, the installed source feed, exact
archive/DLL byte checks and optimized JIT compilation. The PowerShell wrapper
runs the same counted fixture plus the real Windows MI control in STA/MTA and
checks the bundled MMI DLL against the installed source archive. Four test-only
substitutions expose the fixture and give the counted DLL an explicit path.
The small counted driver stays loaded until process exit so exceptional-path
finalizers and cached native delegates remain valid.

For the known affected installed implementation, the standalone wrapper accepts
FEED and --baseline as its second/third arguments. The PowerShell wrapper takes
--baseline as its second argument and requires matching installed bundle/feed.
The counted driver does not open a real CIM connection. Full package checks
exercise the existing real local CIM/WMI paths separately. Authenticated remote
CIM/WSMan and the broader provider/native compatibility audit remain open.

The first package builds passed the initial 80-check fixture but were superseded
before installation after the real control found the immediate-clone defect.
Fresh final builds include the constructor correction and 85-check fixture.
The source audit records all 20 zero-fuzz patches, 73 recipe sources and six
changed/added C# paths. Package/application results and cleanup receipts provide
commands, hashes, logs and remaining requirements; experimental binaries are
not published while dependency completion remains open.

Final clean MMI3 3.0.0-14 and PowerShell 7.4.20-17 builds passed in both
environments. Installed standalone fixtures passed 85 checks each. Installed
PowerShell passed the 85 counted and 17 real Windows MI checks in every STA/MTA
run, including immediate clone disposal with no property read beforehand.
See [package results](package-results-20261108.json) and
[application results](powershell-results-20261108.json) for exact commands,
source/archive/bundle hashes and compiler warnings.

CLANG64's initial BUILDINFO generation overlapped the UCRT64 installation and
reported a missing pacman record. The archive was regenerated with
`makepkg --repackage --force --noconfirm` after all builds/installations were
terminal; its final BUILDINFO contains the stable UCRT64 PowerShell17 record.
The tested payload was retained, and the regenerated archive passed installed
checks. This correction is recorded separately from clean compilation.
