# Transactional FILESTREAM gate

This gate targets the installed source-built System.Data.SqlClient 4.9.1 Windows
implementation. It fills the FILESTREAM gap in the existing real-database
harness; it does not provision SQL Server or enable FILESTREAM.

The live target must be an authorized disposable Windows SQL Server database
with FILESTREAM streaming already enabled and a configured FILESTREAM filegroup.
Windows integrated authentication is required. The current account needs
permission to create and drop a table and stream that database's FILESTREAM data.
Keep settings outside the repository:

```json
{
  "server": "authorized-server\\instance",
  "database": "AuthorizedDisposableDatabase",
  "integratedSecurity": true,
  "encrypt": true,
  "trustServerCertificate": false
}
```

```sh
MINGW_PREFIX=/clang64 bash tests/sqlclient-filestream/check.sh NEW_OUTPUT /private/filestream.json
MINGW_PREFIX=/ucrt64 bash tests/sqlclient-filestream/check.sh NEW_OUTPUT /private/filestream.json
```

The harness generates its own table name, inserts a seed, and checks native
SqlFileStream reads, a large committed overwrite, seek/append, SQL visibility,
rollback isolation and a fresh stream after rollback. Streams close before
transaction completion. It also checks that no active transaction token remains
after commit or rollback. Success requires dropping the owned table and verifying
its absence. Existing tables are not modified. A private output recovery file
identifies the generated table if interruption or cleanup failure leaves it behind;
an operator can inspect/drop that exact table on the configured test database.
The table explicitly selects an existing writable FILESTREAM filegroup, preferring
the configured default; it does not require that filegroup to be the default.

Source/package identity checks run before connection and after streaming. Public
logs print exception types and SQL error numbers, and results hash the endpoint;
they do not print credentials, transaction tokens or FILESTREAM UNC paths.

For compilation, package selection and offline settings validation:

```sh
MINGW_PREFIX=/clang64 SQLCLIENT_FILESTREAM_BUILD_ONLY=1 bash tests/sqlclient-filestream/check.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 SQLCLIENT_FILESTREAM_BUILD_ONLY=1 bash tests/sqlclient-filestream/check.sh NEW_OUTPUT
```

Preparation validates integrated authentication, default TLS policy, disabled
pooling, rejection of SQL credentials/empty settings, and the actual Windows
source DLL. It opens no connection. Build-only success does not verify native
FILESTREAM operation, commit/rollback behavior or SQL Server interoperability.
The live gate remains pending authorized settings; no SQL Server EULA is accepted,
engine started, service changed or database modified during preparation.

The design follows the pinned upstream
[SqlFileStream manual tests](https://github.com/dotnet/maintenance-packages/blob/84b081710c66cc560b77d4de38cee493c3a38e9d/src/System.Data.SqlClient/tests/ManualTests/SQL/SqlFileStreamTest/SqlFileStreamTest.cs)
and Microsoft's
[FILESTREAM transaction context contract](https://learn.microsoft.com/en-us/sql/t-sql/functions/get-filestream-transaction-context-transact-sql)
and [streaming application guidance](https://learn.microsoft.com/en-us/sql/relational-databases/blob/create-client-applications-for-filestream-data).

See [preparation results](build-results-20261109.json) and
[temporary cleanup](cleanup-20261109.json). Production packages are unchanged.
