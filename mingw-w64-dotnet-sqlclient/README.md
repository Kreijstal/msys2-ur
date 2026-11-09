# Experimental SqlClient4.9.1 source package

This is the complete Windows source implementation from dotnet/maintenance-packages
commit `84b081710c66cc560b77d4de38cee493c3a38e9d`, identified by the published4.9.1
nuspec. Archive SHA256:
`f5b1bd0cf8b2c6e232ff866a4f3b069c30c48f37820c10c81691de211d4ba3c6`.
The package remains experimental: LocalDB, shared memory, FILESTREAM and real
SQL Server/native feature parity are still required. It is not counted as a
completed direct dependency in the PowerShell goal tracker.

All242 selected original Windows compiler inputs, the three-source generic
unsupported-platform facade and original project/platform selections are retained.
The actual Windows SqlFileStream implementation is included. Assembly4.6.1.6,
file4.9.1.0, informational4.9.1+source commit and Microsoft b03f5f7f11d50a3a
public-signing identity remain. Public signing does not provide Microsoft's
private-key signature. Original resources are rebuilt from407 strings and the
SQL metadata XML. Vendor implementation binaries are never build inputs or payloads.

The native package installs `system.data.sqlclient.4.9.1.nupkg` in the source feed.
It includes `ref/net8.0`, the original `lib/net8.0` unsupported-platform facade,
and the complete source-managed Windows `runtimes/win/lib/net8.0` implementation.
There is no synthetic/empty native SNI package. The proprietary SNI PackageReference
is removed because the explicit Release port selects the original managed transport.
All framework references, actual compiler inputs, resource inputs, implementation/
reference hashes, wrapper projects, exact overlay sources/patches, removed binary
inventory, original package documentation and MIT license are recorded/shipped.

Ten production overlays preserve the pinned source tree:

1. Select the original managed SNI in Release and Debug, without a Debug environment
   switch. The original Release factory selects proprietary `sni.dll`.
2. Pass complete service principal names to Windows SSPI rather than treating a
   complete SPN, including a pipe suffix, as a DNS IDN hostname.
3. Accept short custom pipe paths such as `\\.\pipe\acct` while retaining the
   nonempty pipe-name check.
4. Honor the inclusive MC-SMP send-window boundary in all three synchronous/queued
   send comparisons. A strict upper-bound comparison stalls after sequence3 with
   WNDW4. The owned protocol test reproduces that failure and then requires sequence4,
   six send-window stalls/resumes across25 DATA frames, ten fragmented response
   frames, multiple receive-credit ACKs, ordered public-reader rows, GC and DONE.
   See [the MC-SMP header specification](https://learn.microsoft.com/en-us/openspecs/windows_protocols/mc-smp/4ada62f7-33c2-45bb-980c-f566f5a6c11a).

5. Query LocalDB buffer sizes, preserve failed startup HRESULTs, and bound
   insufficient-buffer retries. Reject empty/invalid native outputs.
6. Resolve LocalDB's native message formatter through the managed LocalDB loader.
7. Use LocalDB-specific error messages for both SNI backends. The pipe-parser
   overlay also stops transport routing after LocalDB lookup failure.

8. Validate SQL Browser port response sizes, case-insensitive protocol keys,
   numeric ports and duplicate fields.
9. Add explicit local-only LPC/SQLLocal routing, retaining TLS target names and
   Shared Memory Provider errors through the pipe implementation.
10. Atomically publish the command async-state cache shared by command-start
    and write-completion paths.

The original142 selected TDS protocol/endpoint/server fixture inputs are built.
One test-only PlaceholderStream overlay returns partial handshake reads to.NET8
SslStream; the old attempt to fill the larger caller buffer deadlocks negotiation.
An owned temporary certificate replaces the upstream binary certificate fixture;
it is removed without changing trust stores. Original protocol, TLS and server SSPI
implementations remain. Independent SMP peers supplement those original fixtures.

The package check restores through fresh caches using only source-built NuGet
packages and validates actual compiler/reference/generic/Windows runtime selections.
It exercises18 combinations of TCP, long/short named pipes, plaintext, requested/
required TLS, untrusted certificate rejection and integrated Windows SSPI. The
server requires an authenticated current-user Windows identity; its original `NTML`
query marker does not distinguish NTLM and Kerberos. Basic MARS checks cover two
simultaneously open readers, interleaved rows, GC, DONE, session reuse and FINs.
The new MC-SMP window test covers send/receive flow control. Value/clone/record,
all1020 original contract API declarations, all resources/XML and actual source
PowerShell scalar/reader/schema/DONE operations use the restored Windows package.
These are owned protocol fixtures, not a SQL Server database engine.

Build in MSYS2 CLANG64 with `makepkg --cleanbuild --force --noconfirm`. After
installation, extract/verify the pinned archive to a new source path and run:

```bash
/usr/bin/python3 extract.py maintenance-packages-84b081710c66cc560b77d4de38cee493c3a38e9d.tar.gz NEW_SOURCE
bash check.sh NEW_OUTPUT NEW_SOURCE
```

The source audit derives exact selected compiler inputs from the archive and replays
all twelve production patches with zero fuzz. The separate full test audit also checks
all142 original TDS fixture inputs and their one test-stream overlay. Fresh consumers
must load no proprietary SNI or Framework implementation. No policy, persistent PATH,
trust-store, registry, service, firewall or database configuration is changed.

Remaining: LocalDB automatic/named/shared-instance discovery and connections; `lpc:`
shared memory and full native feature parity; real transactional FILESTREAM/database
interoperability; broader TLS trust/host and remote/domain authentication policies;
MARS error/cancellation/combined-encryption/full SMP conformance; complete shipping
PowerShell/compatibility integration and actual runtime servicing. The runtime used by current validation is source-built .NET 8.0.31. Packaging and passing fixture tests do not close these requirements.

Earlier three-overlay source-port evidence is retained in
[`sqlclient-source-sni-results-20261027.txt`](https://github.com/Kreijstal/dotnet-mingw-bootstrap/tree/master/workflows/powershell-deps/sqlclient-source-sni-results-20261027.txt).

Release 2 corrects LocalDB startup and error routing. It queries the native API
for its output size before starting, checks each HRESULT, retries bounded buffer
size changes, rejects invalid/empty successful outputs and preserves native
error codes. Failed LocalDB lookup stops transport selection. Managed SNI loads
LocalDBFormatMessage from the LocalDB API library instead of proprietary SNI,
and both SNI backends now use the LocalDB-specific message path.

The LocalDB ABI gate uses an owned native driver, installed-source consumers and
public SqlConnection Open/OpenAsync failure paths. It does not load an actual
LocalDB installation, start a SQL Server engine or change registry/configuration.
The original no-installation/named/shared-instance/real-engine interoperability
requirements remain open. Run `bash check-localdb.sh NEW_OUTPUT` after installing.

Release 3 validates SQL Browser named-instance and DAC port replies. Transport
keys are matched case-insensitively as keys, duplicate TCP entries and invalid
numeric ports are rejected, instance replies are bounded to 1024 data bytes,
and DAC replies must contain exactly six bytes with a nonzero port. Invalid
responses follow the normal SqlException connection-error path. The loopback
UDP fixture reserves port 1434 exclusively while running; it does not install
or start SQL Browser. It tests direct discovery and public named-instance/DAC
Open/OpenAsync and scalar queries against an independent TDS peer.
Run `bash check-browser.sh NEW_OUTPUT` after installation.

Release 4 adds explicit local-only `lpc:` routing to the SQLLocal instance
endpoint, following Microsoft go-mssqldb commit
`6c346b78c201e490ca2585f0987ddd8f6b4f06a3`. It accepts local aliases, machine name
and loopback IP addresses, rejects remote hosts/ports/invalid instance paths,
and skips SQL Browser. Pipe I/O retains the caller's TLS target name and reports
Shared Memory Provider errors. Normal TCP/NP selection is unchanged.
The source reference and BSD-3-Clause notices are included with the MIT source
license in the NuGet and native packages.

`bash check-lpc.sh NEW_OUTPUT` exercises an owned uniquely named SQLLocal pipe,
public sync/async plaintext and TLS queries, untrusted-certificate rejection,
parser restrictions and provider errors. It starts no SQL Server engine and
changes no SQL/Windows service or registry settings. These fixtures do not prove
actual server interoperability. The separate read-only real-server gate must
observe `net_transport = Shared memory`; LocalDB, FILESTREAM and broader native
compatibility remain open.

Release 5 atomically publishes one SqlCommand async-state cache. The internal
async-start and write-completion paths can initialize this cache concurrently;
two independent caches lose reader/End-method state and can produce a false
EndExecuteReader-called-twice error on fast local transport. The regression
checks 1024 paired starts, shared identity and retention of both actors' state.
This does not make public concurrent execution of a SqlCommand supported.
Run `bash check-async-cache.sh NEW_OUTPUT` after installation.
