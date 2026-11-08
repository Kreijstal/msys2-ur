# SqlClient LocalDB startup port

SqlClient 4.9.1-2 fixes failed LocalDB startup routing, preserves native HRESULTs,
negotiates output buffer sizes with bounded retries, and uses the native LocalDB
message formatter with managed SNI. Both CLANG64 and UCRT64 clean package builds
and fresh installed-source consumers pass 26 owned native ABI checks each.

```sh
bash tests/sqlclient-localdb/check.sh NEW_OUTPUT
```

The recipe contains the primary C# consumer, native driver and test runner. The
native driver implements controlled LocalDB API results without an engine or
registry changes. Tests cover Unicode names/messages, size negotiation, invalid
sizes, repeated growth, failed calls, routing, and public Open/OpenAsync errors.
The installed 4.9.1-1 baseline reproduces ignored HRESULTs and lost failure routing.

The original package gates also pass: 242 implementation/3 contract compiler
inputs, 142 original protocol fixture inputs, 1020 API signatures, 407 resources,
18 transport/TLS/SSPI scenarios, MARS flow control and source PowerShell peers.
[Package results and evidence](package-results-20261108.json) retain exact hashes,
commands, initial fixture failures and remaining requirements.

For actual PowerShell bundle integration, build the same assertions as a library:

```sh
bash tests/sqlclient-localdb/build-powershell-fixture.sh NEW_FIXTURE
pwsh -NoLogo -NoProfile -NonInteractive -STA -File tests/sqlclient-localdb/PowerShellLocalDb.ps1 -Fixture NEW_FIXTURE/bin/Release/net8.0-windows/PowerShellLocalDbFixture.dll -Driver NATIVE_DRIVER.dll
```

Repeat in MTA. The script verifies that PowerShell loads its own bundled SqlClient
and that its bytes match the installed source archive before invoking the checks.

This gate does not prove real SQL Server, actual LocalDB discovery/connections,
LPC/shared memory, transactional FILESTREAM or full authentication compatibility.
The package remains experimental and its binaries are held from publication.
