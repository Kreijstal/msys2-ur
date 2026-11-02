# Microsoft.Security.Extensions Windows source replacement

This package builds the Microsoft.Security.Extensions **1.4.0** public contract
from source for the source-built .NET 8 toolchain on Windows x64. It implements
all 29 published public/protected declarations, assembly
`getfilesiginforedistwrapper, Version=10.0.0.0, PublicKeyToken=31bf3856ad364e35`.
Its informational version is `1.4.0-msys2-source-port+wintrust`.
Public signing preserves the reference identity; it is not a Microsoft signature.
No proprietary implementation assembly or getfilesiginforedist.dll is used.

The C# wrapper calls the source-built `msys-file-signature.dll`. This uses
Windows WinTrust/crypt32 and the `WTGetSignatureInfo` ABI documented in the
MIT-licensed PowerShell 6.2.0 source. Exact source URLs and hashes are in
`source-provenance.json`. The source port requests catalog-first and embedded
verification and OS-binary information without UI. Trust and signature presence
are distinct: self-signed signatures remain present and untrusted. A native
verification failure or missing signing certificate cannot produce trusted status.
The selected provider signing certificate and first countersigner certificate
are copied to independently owned managed X509Certificate2 objects before native
WinTrust state and certificate buffers are freed. Callers own those certificates.
The caller's FileStream stays open and its native position is restored. Calls
use an STA for COM-based providers; no caller apartment is changed.

The package contains the managed net8.0 assembly and its Windows x64 native
NuGet asset. Build/check dependencies include source-built osslsigncode 2.14,
OpenSSL, Clang and the source-built Roslyn metadata inspector. The checks generate
owned PE/PowerShell-script fixtures and temporary self-signed signer/TSA keys.
They require unsigned, embedded-untrusted, offline-timestamped, corrupted and
Windows catalog-trusted results, certificate identity/lifetimes, parallel calls,
renamed/handle-only streams, replacement of an unsigned open stream's path by a
trusted Windows executable, position preservation, argument validation and
bounded kernel-handle use. Test certificates are never added to any trust store.
The independent metadata gate requires all 29 declarations with no extras.

Build under MSYS2 CLANG64:

    makepkg --cleanbuild --force --noconfirm

After installing the package, test a consumer restored only from the installed
feed, with a new cache and output directory:

    bash mingw-w64-dotnet-security-extensions/check.sh NEW_CONSUMER
    bash mingw-w64-dotnet-security-extensions/check-api.sh NEW_CONSUMER NEW_API

This is a source replacement for the public contract, not the vendor's private
implementation. Policy and chain decisions use the host Windows trust providers
and installed roots. Revocation, explicit distrust, expired chains, multiple
signatures, enterprise policy and other provider/file-format combinations still
need wider integration coverage. Full PowerShell Get-AuthenticodeSignature
integration remains required. An unavailable Windows entry point produces an
explicit failure rather than a synthetic trust decision.
