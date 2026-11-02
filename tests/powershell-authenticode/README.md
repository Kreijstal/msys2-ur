# Packaged PowerShell Authenticode integration

`bash tests/powershell-authenticode/check.sh NEW_OUTPUT` generates owned PE and
PowerShell-script fixtures with temporary signer/TSA certificates and executes
packaged PowerShell in both STA and MTA. No certificate is installed into a trust
store. The test checks unsigned PE/script, self-signed PE/script, an offline
timestamped PE, a tampered PE and a Windows catalog-signed OS binary. It verifies
signer/timestamp identities and compares the actual loaded source wrapper/native
provider bytes with the installed Microsoft.Security.Extensions1.4.0 archive.

PowerShell7.4.20 intentionally falls back to WinVerifyTrust for every non-valid
source-provider result. Its MshSignature.cs leaves an untrusted-root HRESULT as
UnknownError. Therefore the self-signed fixtures require UnknownError from the
cmdlet and SignedAndNotTrusted/UntrustedRoot from the direct source provider.
Tampered content must report HashMismatch; catalog trust must report Valid.
The initial incorrect NotTrusted test expectation and its correction are retained
in the evidence. Production code was not changed.

This establishes seven local cases in each apartment. Revoked, explicitly
distrusted and expired chains, enterprise policy, multiple signatures and broader
provider/file-format compatibility remain open. Complete vendor private-behavior
and full PowerShell/dependency compatibility are not claimed.
