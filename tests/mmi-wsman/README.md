# Authenticated WSMan integration

The harness is prepared for an authorized HTTPS/WSMan server. It does not
configure listeners, start WinRM, create accounts, change authentication or
modify remote classes/instances.

From CLANG64 or UCRT64, build against the installed source-only feed and run:

```sh
bash tests/mmi-wsman/check.sh NEW_OUTPUT /private/endpoint.json
```

Keep the private JSON outside the repository with restricted access:

```json
{
  "host": "authorized-test-host.example",
  "port": 5986,
  "domain": "TEST-HOST",
  "username": "temporary-test-user",
  "password": "SET_ONLY_IN_THE_PRIVATE_FILE",
  "namespace": "root/cimv2",
  "className": "Win32_OperatingSystem",
  "allowUntrustedCertificate": false,
  "testInvalidPassword": false
}
```

The account must already have permission to read the chosen WMI namespace and
class over WSMan. The default query is read-only. TLS certificate checks are on
by default. The optional certificate bypass applies only to this process's test
options. Use the incorrect-password test only with an authorized disposable
account and known lockout policy; it is off by default and runs after positive
connections. Its expected AccessDenied mapping still requires real-server
validation.

The positive path tests explicit Negotiate credentials copied into native
options, independent option cloning after the caller's password buffer is
cleared/disposed, TestConnection, class metadata, synchronous/asynchronous
queries, retained result lifetime, callback-root cleanup and a fresh reconnect.
Public console/result logs omit passwords, account names and the endpoint name.
The endpoint is represented only by a hash in the result JSON. Native failure
text is not printed because it may contain private identifiers.

For preparation without a server or credentials:

```sh
MMI_WSMAN_BUILD_ONLY=1 bash tests/mmi-wsman/check.sh NEW_OUTPUT
```

This builds from a fresh cache, checks the restored archive and runtime DLL
against the installed source feed, and runs eight offline settings/native-option
clone and password-copy/readback checks with dummy credentials. It opens no connection and does not prove
remote authentication. The live authenticated run is pending an authorized
endpoint and a private credentials-file path. The test host's WinRM service
remains stopped; its existing wildcard HTTP listener has not been enabled.
