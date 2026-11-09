# SqlClient SQL Browser discovery

The Windows managed SNI port in SqlClient 4.9.1-2 rejects mixed-case `tcp` keys,
accepts malformed/duplicate ports, confuses field values with transport keys,
and reads truncated DAC replies without checking their complete length.
Public OpenAsync can leak FormatException/ArgumentException instead of SqlException.

Release 3 validates named-instance reply sizes and numeric ports, matches protocol
keys case-insensitively, ignores values when selecting transport keys, rejects
duplicate TCP keys, and requires exactly six bytes and a nonzero port in DAC replies.
The production change is confined to the original SSRP implementation; it adds
no public API and preserves the pinned original sources through an explicit overlay.

The independent fixture sends real UDP replies on loopback port 1434. It reserves
that endpoint exclusively and fails if it is in use. A per-session named mutex
serializes the two package test processes; no existing service is stopped or
reconfigured. All sockets and the mutex are disposed. It checks exact request
bytes, valid and invalid replies, public connection errors, and successful sync
and async named-instance/DAC scalar queries against its independent TDS peer.
The peer is a protocol fixture, not a SQL Server database engine.

The final installed release-2 baseline reproduces 19 defects in 61 assertions.
An earlier fixture run hit a test-only Mutex thread-affinity error after reporting
the reproductions. The corrected wrapper acquires/releases the mutex on the same
thread while waiting for asynchronous peer work; its final baseline exits zero.

```sh
MINGW_PREFIX=/clang64 bash tests/sqlclient-browser/check.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/sqlclient-browser/check.sh NEW_OUTPUT
MINGW_PREFIX=/clang64 bash tests/sqlclient-browser/check-powershell.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/sqlclient-browser/check-powershell.sh NEW_OUTPUT
```

Standalone baseline mode takes `--baseline` as the third argument after OUTPUT
and FEED. PowerShell baseline mode takes it as the second argument after OUTPUT.
Each consumer uses a new output and NuGet cache and checks source archive/DLL
identity. The PowerShell wrapper checks the actual bundled DLL in STA and MTA;
it changes only the fixture class visibility/name when building its library.

This does not establish complete SQL Browser conformance, DNS/remote/domain
behavior, real SQL Server or LocalDB connectivity, shared memory, or FILESTREAM.
The full PowerShell dependency goal and SqlClient package remain incomplete;
experimental binaries are held from publication.

The parsing rules follow Microsoft's [MC-SQLR message syntax](https://learn.microsoft.com/en-us/openspecs/windows_protocols/mc-sqlr/def8dec4-5c2b-4bfd-9531-655de3f74954),
[instance response](https://learn.microsoft.com/en-us/openspecs/windows_protocols/mc-sqlr/2e1560c9-5097-4023-9f5e-72b9ff1ec3b1), and
[DAC response](https://learn.microsoft.com/en-us/openspecs/windows_protocols/mc-sqlr/45b52721-7a48-45cf-9c84-e6db905ad6df).

Both CLANG64 and UCRT64 release-3 packages pass clean
`makepkg --cleanbuild --force --noconfirm` builds, including existing API,
resource, transport/TLS/SSPI, MARS and LocalDB gates. Fresh installed consumers
pass 94 assertions with zero defects. Compiler-input comparison against release
2 proves that SSRP.cs is the sole changed implementation input; the other 241
implementation inputs and all three contract inputs are unchanged.

See [package results](package-results-20261109.json) and
[source audit](source-audit-20261109.json). The inherited audit status text still
says four overlays; its independently checked metadata records the actual eight
overlays and nine production patches.

PowerShell 7.4.20-19 also passes both clean package builds. Each actual installed
bundle passes 94 SQL Browser assertions in STA and MTA, with its SqlClient DLL
matching the installed source archive byte for byte. All compiler invocations
report zero errors; SDK builds retain three CA1846 warnings each and the CLANG64
desktop console retains one NETSDK1106 warning.
[PowerShell results](powershell-results-20261109.json) and
[temporary build cleanup](cleanup-20261109.json) record the final integration.
