# Real SQL Server and LocalDB integration

Run in an MSYS2 CLANG64 or UCRT64 shell against the installed source-built
SqlClient 4.9.1:

```sh
MINGW_PREFIX=/clang64 bash tests/sqlclient-realdb/check.sh new-output /private/connection.json
```

Use `/ucrt64` for the UCRT64 environment. Keep private settings outside the
repository with restricted access. For SQL authentication, supply `server`,
`user` and `password` strings. For Windows authentication, supply `server` and
`"integratedSecurity": true`, with no `user` or `password` fields. SQL authentication
remains the default for existing settings files.

For the separate Windows LocalDB gate, use an authorized instance, for example:

```json
{
  "server": "(localdb)\\MSSQLLocalDB",
  "integratedSecurity": true,
  "requireLocalDB": true
}
```

The explicit LocalDB mode requires both a LocalDB discovery address and Windows
authentication. Before creating databases, it requires the connected engine's
`SERVERPROPERTY('IsLocalDB')` to equal 1 and its transport to be `Named pipe`.
Full-server mode requires `IsLocalDB` to equal 0. This prevents an ordinary server
or a direct pipe connection from being counted as successful LocalDB discovery.
Connecting to LocalDB can automatically create/start its per-user instance;
run live mode only when that action is authorized. See Microsoft's
[LocalDB connection documentation](https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/sql-server-express-localdb)
and [server property reference](https://learn.microsoft.com/en-us/sql/t-sql/functions/serverproperty-transact-sql).

The authenticated principal needs permission to create and drop databases.
Use a disposable test server: the harness creates uniquely named databases and
drops them in `finally` blocks. It never intentionally modifies existing
databases. If the process is killed, its test databases may need manual cleanup.

Full-server mode retains both plaintext and encrypted session tests and requires
an untrusted certificate for its negative certificate test. The initial connection
explicitly trusts the test server's certificate. LocalDB mode runs the same
parameter/transaction/bulk/MARS/error/cancellation scenarios over its local named
pipe with encryption disabled; it does not establish TLS interoperability.
Real shared-memory transport and FILESTREAM remain separate gates.

The harness restores exclusively from the selected environment's installed
source package feed and checks the restored archive and runtime DLL against
that feed. It exercises typed parameters, Unicode, large binary streams,
transactions/savepoints, bulk copy, datasets, stored procedure outputs, multiple
result sets, MARS, server errors, and timeout/cancellation recovery. Successful
live execution writes `new-output/results.json`, with separate LocalDB and TLS
verification fields. Failure output includes the exception type and SQL error
number, without printing connection settings or exception messages.

For compilation, exact source-package selection and offline authentication/settings
checks without a server or private settings:

```sh
MINGW_PREFIX=/clang64 SQLCLIENT_REALDB_BUILD_ONLY=1 bash tests/sqlclient-realdb/check.sh new-output
```

Every run performs offline checks and writes `preparation-results.json` and
`source-identity.json`. Build-only mode never opens a server connection and
**does not establish SQL Server or LocalDB interoperability**.

The [2026-11-09 preparation evidence](build-results-20261109.json) records both
environments. Live gates remain pending: the host inventory found no SQL Server
service or installed LocalDB version. No engine was started or EULA accepted.
The original [2026-11-08 results](build-results-20261108.json) are historical
compilation evidence for the earlier SQL-login-only harness.
