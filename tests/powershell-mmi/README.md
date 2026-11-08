# PowerShell integration of source MMI3

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
