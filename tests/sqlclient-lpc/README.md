# SqlClient explicit LPC transport

Release 5 includes explicit local-only `lpc:` routing to the Windows SQLLocal
instance endpoint. The reference is Microsoft's
[go-mssqldb implementation](https://github.com/microsoft/go-mssqldb/blob/6c346b78c201e490ca2585f0987ddd8f6b4f06a3/sharedmemory/sharedmemory_windows.go)
and its [real-server transport assertion](https://github.com/microsoft/go-mssqldb/blob/6c346b78c201e490ca2585f0987ddd8f6b4f06a3/sharedmemory_test.go).
The BSD-3-Clause reference notices accompany the original MIT license in both
package formats. No Go toolchain or vendor SNI binary is used.

The port accepts local aliases, the machine name and loopback IPs; rejects
remote hosts, TCP ports and invalid instance paths; chooses
`\\.\pipe\SQLLocal\INSTANCE` (MSSQLSERVER by default); and skips SQL Browser.
Explicit LPC keeps its own protocol identity and has no TCP/normal-NP fallback.
Existing TCP/NP selection is retained. The pipe implementation accepts separate
physical pipe and TLS target hosts and reports Shared Memory Provider errors.
SSPI uses the host/instance service target. MultiSubnetFailover retains the
original non-TCP ArgumentException contract.

The independent fixture reserves a uniquely named, current-user-only SQLLocal
pipe. It checks parser restrictions, exact endpoint selection, TLS/provider/SPN
fields, public sync/async scalar queries over plaintext and TLS 1.2, and rejection
of an untrusted owned certificate. The candidate passes 144 assertions. The
installed SqlClient 4.9.1-3 / PowerShell 7.4.20-19 baseline reproduces 30 defects
in ten successful control assertions in standalone and STA/MTA runs.

Initial fixture iterations corrected an IDisposable assumption for an internal
SNI handle, the expected MultiSubnetFailover exception type, Schannel's need for
a provider-backed temporary certificate key, and cleanup after an expected TLS
rejection. One early TLS fixture timed out; final peer deadlines close only the
owned pipe. Keys/certificates are disposed without trust-store changes.

```sh
MINGW_PREFIX=/clang64 bash tests/sqlclient-lpc/check.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/sqlclient-lpc/check.sh NEW_OUTPUT
MINGW_PREFIX=/clang64 bash tests/sqlclient-lpc/check-powershell.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/sqlclient-lpc/check-powershell.sh NEW_OUTPUT
```

The standalone wrapper's optional arguments are FEED and `--baseline`.
The PowerShell wrapper accepts `--baseline` after OUTPUT. It changes only fixture
class visibility/name and tests the actual bundled DLL in STA and MTA after
checking its bytes against the installed source archive. Each output/cache must
be fresh. These are protocol fixtures, not SQL Server engines.

The first release-4 clean package runs passed, but a fresh UCRT64 consumer
exposed an intermittent EndExecuteReader-called-twice failure. The async-start
and write-completion paths could create separate command-state caches. A
1024-pair baseline reproduced 318 identity splits and 318 lost metadata values.
A test-only widened scheduling window reproduced the public failure with the
same execution task using different cache identities at Set and End. Atomic
publication fixes the cache identity: 1024 paired starts retain both metadata
values, and 128 concurrent public queries also pass with that widened window.
The regression does not promise public concurrent execution of one SqlCommand.

The PowerShell fixture includes both 144 LPC checks and the separate 1024-pair
cache check in each STA/MTA mode. Its optional third argument selects the source
archive for a historical baseline; normal validation uses the installed archive.
The diagnostic DLLs and packages used for the widened-window experiment are
private test artifacts, not the production source-port payload.

For the separate read-only real Windows SQL Server gate:

```sh
MINGW_PREFIX=/clang64 bash tests/sqlclient-lpc/check-real.sh NEW_OUTPUT /clang64/lib/dotnet/library-packs /private/lpc.json
```

The private JSON contains `server` (an explicit `lpc:` local instance), optional
`integratedSecurity` (default true), `user`/`password` for SQL authentication,
`encrypt` (default false), and `trustServerCertificate` (default false). Keep it
outside the repository. The authorized account needs permission to inspect its
connection in sys.dm_exec_connections. The gate opens master and only reads
server/transport metadata; it must observe `net_transport = Shared memory` and
an actual Microsoft SQL Server version. It checks restored source implementation
selection and absence of proprietary SNI/Framework helpers. Failure logs omit
endpoint names and native exception text. It configures no services or protocols.

`SQLCLIENT_LPC_BUILD_ONLY=1` with OUTPUT and FEED compiles and verifies package
selection without reading settings or opening a connection. A successful fixture
or build-only run does not establish real-server LPC interoperability. Actual
Windows SQL Server, LocalDB/FILESTREAM, remote authentication and complete native
compatibility remain open. Experimental binaries are held from publication.

The [release-5 package results](package-results-20261109.json) record clean
`makepkg --cleanbuild --force --noconfirm` builds and fresh installed consumers
in CLANG64 and UCRT64. Both environments pass 144 LPC assertions and 1024 cache
publication checks. The [source comparison](source-audit-20261109.json) retains
all 242 implementation and three generic-contract inputs: only SNIProxy.cs,
SNINpHandle.cs and SqlCommand.cs differ from release 3. The
[evidence directory](evidence-20261109/) includes the original intermittent
failure and the diagnostic scheduling-window reproduction alongside final results.
The real LPC harness compiles with zero warnings and errors in both environments;
no real-server connection was attempted.

PowerShell 7.4.20-21 clean builds and fresh installed STA/MTA runs pass in both
CLANG64 and UCRT64: each mode passes 144 LPC assertions and 1024 cache checks.
The [PowerShell results](powershell-results-20261109.json) bind build logs,
source inputs and bundled DLL hashes to the installed SqlClient 4.9.1-5 archive.
[Cleanup](cleanup-20261109.json) removes the temporary build roots and staged
archives after saving text evidence, while retaining installed packages and recipes.
