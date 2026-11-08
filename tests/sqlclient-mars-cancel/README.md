# SqlClient MARS cancellation, errors and TLS

This fixture exercises installed source-built System.Data.SqlClient 4.9.1-2 and
its bundled implementation in PowerShell 7.4.20-14 on .NET 8.0.31, in CLANG64
and UCRT64. It uses an owned loopback TDS/SMP peer, with fragmented frames,
and does not start a SQL Server engine.

Each run checks four failure modes over both plaintext TCP and TLS 1.2:

- `SqlCommand.Cancel` on a pending reader.
- CancellationToken cancellation on `ReadAsync`.
- CommandTimeout expiration.
- Server ERROR 50001 with DONE_ERROR.

The peer verifies ATTENTION routing to the correct logical MARS session and
returns DONE_ATTN for the three cancellation modes. An independent reader
survives cancellation, reader disposal and compacting GC. A third command
verifies connection recovery. The server-error case requires zero ATTENTION
packets. The fixture also checks the loaded source implementation and absence
of proprietary SNI/Framework helper modules.

Run from an MSYS2 shell with the relevant installed prefix:

```sh
MINGW_PREFIX=/clang64 bash tests/sqlclient-mars-cancel/check.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/sqlclient-mars-cancel/check.sh NEW_OUTPUT
MINGW_PREFIX=/clang64 bash tests/sqlclient-mars-cancel/check-powershell.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/sqlclient-mars-cancel/check-powershell.sh NEW_OUTPUT
```

Each output directory must be new. Restore uses only the installed library-packs
feed and a fresh cache. The PowerShell wrapper runs the same fixture in STA and
MTA and verifies the bundled SqlClient DLL against its installed source archive.
Its two test-only substitutions expose the class and entry point as a callable
library; production code and package recipes are unchanged.

The recorded run passed 448 assertions in each of two standalone and four
PowerShell executions: 48 scenarios total. Commands, source hashes, archive/DLL
hashes and log paths are in [results-20261108.json](results-20261108.json).
The UCRT64 prefix was exercised from a CLANG64 orchestration shell.

TLS uses an owned self-signed certificate with TrustServerCertificate enabled.
These scenarios verify encrypted cancellation/error isolation; certificate and
hostname policy require separate validation. The initial TLS fixture failed
because Schannel rejected its ephemeral server key. Exporting/importing the
owned certificate with DefaultKeySet corrected the fixture; no trust-store
installation or persistent-key flag is used. The original failure log is kept.

Real SQL Server/LocalDB, LPC/shared memory, transactional FILESTREAM, remote and
domain authentication, broader MARS races/pooling and full native SNI parity
remain open. This evidence does not make the dependency complete.

Protocol references: [ATTENTION](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-tds/dc28579f-49b1-4a78-9c5f-63fbda002d2e),
[DONE_ATTN](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-tds/f8aa004e-bf76-4f94-bd5b-39597a888146),
[TLS handshake encapsulation](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-tds/cc823ca8-4867-4387-819d-cc5c19da5732),
[encrypted traffic after the handshake](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-tds/d62e225b-d865-4ccc-8f73-de1ef49e30d4).
