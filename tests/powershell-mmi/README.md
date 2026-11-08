# PowerShell integration of MMI3 3.0.0-2

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
