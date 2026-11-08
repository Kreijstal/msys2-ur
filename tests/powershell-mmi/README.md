# PowerShell integration of source MMI3

## Metadata-view cleanup: PowerShell 7.4.20-7 (2026-11-08)

PowerShell **7.4.20-7** bundles **MMI3 3.0.0-5**, including automatic cleanup of
abandoned qualifier-set and parameter-set wrapper allocations. Clean CLANG64
and UCRT64 `makepkg --cleanbuild --force --noconfirm` runs passed every original
source build, provenance/license/API audit and package check. CLANG64 also
passed the original desktop build and rendering checks.

The new `MetadataSmoke.ps1` runs the original `Get-CimClass` cmdlet and traverses
real Win32_Process class/property/method/parameter qualifiers, forcing compacting
GC and checking that the borrowed class metadata remains valid. CLR getters are
invoked directly to expose exceptions that PowerShell property adaptation could
otherwise hide. The fixture compares bundled MMI bytes with the installed source
archive.

After installation, **943 metadata**, **13 MOF**, **34 embedded/event** and
**25 delivery checks** passed in each of STA and MTA, in both environments.
[Exact commands, compiler logs, package/installed results and hashes](metadata-integration-results-20261108.json)
record the evidence. The underlying MMI fix also passed
[2,071 installed metadata ownership checks](../mmi-cim-wmi/metadata-package-results-20261108.json)
per environment, including 192 abandoned wrapper allocations and concurrent GC.

Remote CIM authentication, provider-origin extended callbacks/streams, the
broader native ownership/provider audit, SqlClient and Windows.Compatibility
remain open. These experimental binaries remain unpublished. Earlier records
below retain their original revision and validation scope.

## UCRT64 current-revision integration (2026-11-08)

PowerShell **7.4.20-6** with **MMI3 3.0.0-4** also passed a clean UCRT64
`makepkg --cleanbuild --force --noconfirm`. Original SDK, console and
LocalAccounts builds, source/catalog/apphost/payload/license audits, all 459
LocalAccounts API declarations and every package behavior check passed. The
UCRT64 recipe omits WindowsDesktop/GraphicalHost; CLANG64 desktop results are
recorded below.

After installation, **13 MOF**, **34 embedded/event** and **25 delivery checks**
passed in each of STA and MTA. The bundled MMI DLL matches the UCRT64 installed
source archive. [Commands, input/artifact hashes and scope](ucrt-integration-results-20261108.json)
link the [clean build/check log](ucrt-package-results-20261108.txt) and
[installed fixture log](ucrt-installed-20261108.txt). The current revisions are
now built and locally tested in both environments. Authenticated remote CIM,
provider-origin extended callbacks/streams, complete ownership/provider parity,
SqlClient and Windows.Compatibility remain open; experimental binaries are
unpublished.

## Native delivery storage: PowerShell 7.4.20-6

The CLANG64 package bundles **MMI3 3.0.0-4**. A clean
`makepkg --cleanbuild --force --noconfirm` passed the original source builds,
source/package/license audits, LocalAccounts API gate and all package checks.
The new `DeliverySmoke.ps1` exercises public construction, credential addition,
intervals, cloning and disposal inside the actual console. It reads native
storage through reflection to verify Unicode domain/user fields, mechanism,
password copying and clone lifetime after original disposal/compacting GC.
Credentials are dummy test data; no remote authentication is performed.

After installation, **13 MOF**, **34 embedded/event** and **25 delivery checks**
passed in each of STA and MTA, including byte comparisons between the bundled
MMI DLL and the installed source archive. The existing original-CIM event
cmdlets, STA WMI, source desktop rendering and six gallery-module checks passed.
[Exact commands, scope and hashes](delivery-integration-results-20261108.json)
link the [clean build/check log](delivery-package-results-20261108.txt) and
[installed STA/MTA log](delivery-installed-20261108.txt).

Run the installed `MofSmoke.ps1`, `EmbeddedSmoke.ps1` and `DeliverySmoke.ps1`
fixtures with `-STA` or `-MTA` and process-local `-ExecutionPolicy Bypass`.
The source archive is needed for the DLL byte comparison. Remote/provider,
broader ownership, SqlClient and Windows.Compatibility gates remain open;
this binary is unpublished. Earlier dated records below retain their original
scope, package versions and hashes.

## Embedded values and real event cmdlets: PowerShell 7.4.20-5

The current package bundles **MMI3 3.0.0-3**. Its original SDK, console,
LocalAccounts and GraphicalHost source builds passed. The first package check
found a fixture bug: `Write-Output -NoEnumerate` wrapped a scalar CIM instance in
a list. Changing the helper to `return ,$value` fixed it. The corrected fixture
was copied into the extracted sources, the distribution/manifest regenerated,
the full package checks rerun, and `makepkg --repackage --force --noconfirm`
completed successfully. Product compiler inputs were unchanged by this fixture
correction; the built source outputs were reused.

After installation, **13 MOF checks** and **34 embedded/event checks** passed in
each of STA and MTA. The latter checks independently owned embedded instances
and references, array snapshots, current flags, empty versus NULL values and
lifetime after disposal/GC. It uses the original `New-CimSession` and
`Register-CimIndicationEvent` cmdlets for a real local DCOM intrinsic process
event, retaining `TargetInstance` after unregistration, session removal,
outer-event disposal and compacting GC. Every run compares the bundled MMI DLL
against the installed source archive.

[Exact commands, hashes, initial failure, final results and remaining scope](embedded-integration-results-20261108.json)
link the [final package check](embedded-package-check-20261108.txt),
[repackage](embedded-repackage-20261108.txt) and
[installed STA/MTA log](embedded-installed-20261108.txt). Run the installed
`MofSmoke.ps1` and `EmbeddedSmoke.ps1` scripts with `-STA` or `-MTA`, passing
`-ExecutionPolicy Bypass` only for that test process. They need the installed MMI
source archive for the byte comparison.

This binary remains unpublished. The recorded source audit found a no-op in
`CimSubscriptionDeliveryOptions.AddCredentials`; MMI3 3.0.0-4 now fixes that and
the delivery constructor/interval/clone paths, with [138 native checks](../mmi-cim-wmi/delivery-package-results-20261108.json).
PowerShell 7.4.20-5 still bundles MMI3 3.0.0-3 and needs another rebuild for those
changes. Remote/provider, broader ownership, SqlClient, Windows.Compatibility
and UCRT64 gates also remain open. The earlier release-4 record below retains its
original scope and hashes.

PowerShell 7.4.20-4 was rebuilt and installed on `win11` in CLANG64. Its bundled
MMI implementation matches the source archive from MMI3 3.0.0-2, including the
MOF include callback, offset and native cleanup patch.

`makepkg --cleanbuild --force --noconfirm` passed the source/package/license
audits, LocalAccounts API gate and all package checks. The new in-process MOF
fixture passed 13 assertions in the staged package, then passed 13 assertions
each in installed STA and MTA processes. It checks bundled MMI bytes, native
Unicode includes, nonzero offsets, retained payload after disposal/compacting GC
and live CIM cmdlets in the actual PowerShell application.

Exact commands, source hashes, package hashes and scope are recorded in
[integration results](integration-results-20261108.json). Logs cover
[the complete package build/check](package-results-20261108.txt),
[installed validation](installed-results-20261108.txt),
[three existing SDK CA1846 warnings](sdk-build-20261108.txt) and
[the desktop console NETSDK1106 warning](desktop-build-20261108.txt).

To rerun the installed fixture from a CLANG64 shell:

```sh
pwsh.exe -NoProfile -NonInteractive -STA -File "$(cygpath -am "$MINGW_PREFIX/share/doc/powershell/checks/MofSmoke.ps1")"
pwsh.exe -NoProfile -NonInteractive -MTA -File "$(cygpath -am "$MINGW_PREFIX/share/doc/powershell/checks/MofSmoke.ps1")"
```

The fixture needs the installed MMI source archive for the byte comparison. It
parses in-memory MOF without registering schemas or instances. Remote/provider,
broader ownership, SqlClient and Windows.Compatibility gates remain open; this
binary has not been published. UCRT64 has not been tested for this revision.
