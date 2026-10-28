# Source-built .NET cryptography, diagnostics and encoding libraries

This CLANG64 split recipe packages six independent libraries from the pinned
**dotnet/runtime v8.0.31** source archive:

| NuGet ID | NuGet version | MSYS2 suffix |
| --- | --- | --- |
| System.Formats.Asn1 | 8.0.2 | dotnet-formats-asn1 |
| System.Security.Cryptography.Pkcs | 8.0.1 | dotnet-cryptography-pkcs |
| System.Security.Cryptography.Xml | 8.0.4 | dotnet-cryptography-xml |
| System.Diagnostics.DiagnosticSource | 8.0.1 | dotnet-diagnosticsource |
| System.Text.Encodings.Web | 8.0.0 | dotnet-encodings-web |
| System.Text.Encoding.CodePages | 8.0.0 | dotnet-encoding-codepages |

MSYS2 package versions identify source release 8.0.31. NuGet versions match the
upstream ServicingVersion declarations and PowerShell 7.4.20 requirements.
Assemblies retain version 8.0.0.0 and the upstream public-signing keys; their
file version is 8.0.31.0 and informational version names the pinned source.

The ASN.1 -> PKCS -> XML dependency chain uses exact references to separate
source-built NuGet packages. PKCS retains upstream ASN XML/XSLT code generation
and shared reader imports. Windows-specific packages expose ref/net8.0 contracts
and runtimes/win/lib/net8.0 implementations; other packages use lib/net8.0.
Reference contracts retain upstream conditional Compile items and type forwards.
Upstream binary software inputs are deleted. The codepages.nlp mapping resource
is retained as upstream encoding data, alongside compiled C# mapping tables.

The targeting pack must be **8.0.131-2 or newer**. The older pack advertised
framework file version 8.0.31.0 even for implementation DLLs built from 8.0.0
sources. MSBuild then discarded these new library implementations. The fixed
pack reads actual runtime PE versions and distinguishes implementations from
forwarding shims. Consumer gates check every assembly's source version, file
version, signing identity and location under the consumer output directory;
a successful test cannot silently use the older inbox implementation.

Build in CLANG64 with the source-built SDK and corrected targeting pack:

```bash
makepkg --cleanbuild --force --noconfirm
```

`check()` builds a plain net8.0 consumer from a new cache/private feed and tests:

- BER/CER/DER, constructed/large values, integers, OIDs, Unicode, times and invalid encodings;
- CMS attached/detached signing and verification, tampering, AES envelopes/wrong keys,
  PKCS12 encryption/password/MAC and certificate/private-key bags;
- XML RSA/SHA256 signatures, wrong-key/tamper rejection, AES and RSA key wrapping;
- DiagnosticListener, Activity sampling/parenting/events/tags and Meter counters;
- HTML/JavaScript/URL escaping, exact Windows1252/Shift-JIS mappings and fallbacks;
- public/protected signatures and forwarded types against separately compiled
  upstream reference contracts.

Cryptographic tests use temporary in-memory keys and self-signed certificates;
signature checks validate signatures without claiming certificate trust. They
do not write certificate stores, contact timestamp/validation services or alter
machine configuration. Native modules are limited to Windows cryptographic APIs;
no .NET Framework helper is allowed. These are functional/dependency checks,
not a full cryptographic security audit or a claim that all runtime servicing
fixes are supplied. The core runtime still uses 8.0.0 sources.

Install all six split packages together, then run with a new output directory:

```bash
bash mingw-w64-dotnet-crypto/check.sh /tmp/powershell-crypto-installed
```

The default source is the installed feed. An optional second argument selects a
private feed. NuGet6.8 can emit NU5131 for ref/runtime-only packages; installed
plain-net8.0 consumers verify Windows runtime asset selection. Complete
PowerShell integration and attribute/layout/generic-constraint/binary
compatibility remain separate validation work.
