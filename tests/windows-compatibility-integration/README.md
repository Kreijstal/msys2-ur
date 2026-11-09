# Windows compatibility integration and runtime selection

The cross-library consumer restores Microsoft.Windows.Compatibility 8.0.31 and
PowerShell's SqlClient 4.9.1 selection from the installed source feed. Its
69 assertions exercise a document pipeline across 13 dependencies: convention
composition, custom reflection, CodeDom, codepages, Atom syndication, signed XML,
GDI+ PNG, compressed OPC packaging, CMS encryption, current-user DPAPI,
configuration save/reopen and cache callbacks. It checks Unicode/newlines,
wrong-entropy rejection and signed-content tampering with temporary owned data.

The fixture loads all 35 direct assemblies and records those plus the transitive
Windows.Extensions assembly. A source ownership check compares the restored
40 archives and 67 consumer DLLs with installed source packages, then verifies
the actual runtime-loaded DLL hashes in standalone and PowerShell STA/MTA modes.
The runtime's inbox CodePages implementation is checked against the installed
8.0.31 source-payload manifest. No provider/server connection is attempted.

```sh
MINGW_PREFIX=/clang64 bash tests/windows-compatibility-integration/check.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/windows-compatibility-integration/check.sh NEW_OUTPUT
```

PowerShell24 CLANG64 passed the document workflow while loading nine older
desktop-framework assemblies. Eight are direct metapackage dependencies;
Windows.Extensions is transitive. The standalone source consumer selected the
serviced packages. The baseline records the loaded paths and hashes rather than
treating successful operations as proof of correct assembly selection.

The correction stamps the nine rebuilt implementations with file version
8.0.31.0 while preserving assembly version 8.0.0.0, signing identities and NuGet
versions. PowerShell staging extracts the exact source package bytes, inspects
their actual PE versions and keeps their runtime entries explicit despite
desktop asset pruning. The payload auditor independently reconstructs the
allowed manifest changes from the original console output. A shipping smoke
requires the nine assemblies to load from the app directory with matching hashes.
EventLog's rebuilt message companion is included; its custom Win32 resource has
no VERSIONINFO and the manifest preserves that absence.

Both source library recipes pass clean builds and their native/API checks in
both environments. All thirty resulting native packages were audited and
installed before PowerShell25's clean builds. Both PowerShell packages pass
their complete shipping checks, including source CIM/WMI, gallery modules,
native children and CLANG64 desktop rendering. Fresh installed consumers pass
all six 69-assertion runs and verify all 36 loaded identities with zero desktop
selection divergences. Existing compiler/deprecation/layout warnings are retained
in the logs; compiler invocations report zero errors.

Final package and installed integration evidence is recorded in
[results](results-20261109.json), with the
[satellite builds](windows-libraries-results-20261109.json) and
[configuration builds](windows-configuration-results-20261109.json),
[compiler summaries](compiler-results-20261109.json),
[source lock validation](source-lock-results-20261109.json) and
[temporary cleanup](cleanup-20261109.json).

Diagnostics retain the initial fixture compile-glob mistake, explicit XML
newline preservation, the real CLANG64 MSBuild resource-path failure and its
focused normalized-path rebuild. The final fixture compiles only Program.cs;
the configuration adapter normalizes pinned source paths without excluding
source files. Baseline fixture/checker snapshots are hash-bound separately.

The workflow covers 13 dependencies behaviorally and checks the wider graph's
runtime selection. Existing per-library tests supply additional coverage.
Authenticated CIM/WSMan, real SQL Server/LocalDB/FILESTREAM and broader provider
compatibility remain unfinished. Experimental binaries remain unpublished.
