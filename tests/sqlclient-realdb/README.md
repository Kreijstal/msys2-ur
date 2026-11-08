# Real SQL Server integration

Run in an MSYS2 CLANG64 shell against the installed source-built SqlClient 4.9.1:

```sh
bash tests/sqlclient-realdb/check.sh new-output /private/connection.json
```

The private JSON file contains `server`, `user` and `password` strings. Keep it
outside the repository with restricted access. The SQL login needs permission to
create and drop databases. Use a disposable test server: the harness creates
uniquely named databases and drops them in `finally` blocks. It never intentionally
modifies existing databases. If the process is killed, its test databases may
need manual cleanup.

The server must allow both plaintext and encrypted TCP sessions and present an
untrusted certificate for the negative certificate test. The test first connects
with certificate trust explicitly enabled. Run only against an authorized test
server with this configuration.

The harness restores exclusively from the installed source package feed and
checks the restored archive and runtime DLL against that feed. It exercises
typed parameters, Unicode, large binary streams, transactions/savepoints,
bulk copy, datasets, stored procedure outputs, multiple result sets, MARS,
server errors, timeout/cancellation recovery and TLS certificate rejection.
Successful execution writes `new-output/results.json`.

For compilation and package-selection validation without a server:

```sh
SQLCLIENT_REALDB_BUILD_ONLY=1 bash tests/sqlclient-realdb/check.sh new-output /private/connection.json
```

The build-only mode does **not** establish SQL Server interoperability. Linux SQL
Server testing also cannot establish Windows LocalDB, shared-memory transport or
FILESTREAM support. The current real-server run is pending a test server and the
user's answer about accepting the SQL Server Developer EULA; no engine has been
started and no EULA accepted by this harness.
