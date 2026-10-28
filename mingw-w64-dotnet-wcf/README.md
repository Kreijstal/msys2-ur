# WCF 4.10.3 for the source-built .NET feed

Seven split packages build System.Private.ServiceModel, System.Web.Services.Description,
and the Primitives, Duplex, Security, Http and NetTcp facades from upstream commit
`6c05fa33450ee3960f0763948e91327f049b302b`. The published 4.10.3 nuspec repository
metadata identifies this commit; upstream has no corresponding v4.10.3 tag.
The source archive SHA-256 is
`fd4a9c4500f811ec600e1570f94672db25aa5fa8129c1aa0704643290b41e8ae`.

The port targets net8.0 with FEATURE_CORECLR and preserves assembly versions
4.10.3.0, the b03f5f7f11d50a3a identity and a source-commit informational version.
A source alias disambiguates WCF's Activity from System.Diagnostics.Activity.
Runtime-provided APIs replace the old DispatchProxy, Vectors, Principal.Windows
and AsyncInterfaces package dependencies. The implementation uses the installed
source-built ObjectPool 8.0.31 and cryptography XML 8.0.4 packages.
Public signing preserves assembly identity without claiming a Microsoft
private-key signature. The underlying runtime still uses 8.0.0 sources.

Each facade package contains its source-built upstream reference contract under
ref/net8.0 and a newly generated runtime forwarder under lib/net8.0. Private's
empty reference placeholder keeps implementation types out of the compile
surface. WSDL has separate reference and implementation assets. The compiler
builds five runtime facades with 5, 29, 10, 182 and 28 root forwards for Duplex,
Http, NetTcp, Primitives and Security respectively.

Primitives also contains a freshly compiled method-free System.ServiceModel
4.0.0.0 compatibility shim with ECMA identity b77a5c561934e089. Its 274 exported
forwards (270 root types, four protected nested types) preserve the original
public facade targets and refer to the separate source-built Syndication 8
package. The shim is compiled against rebuilt reference contracts so forwarding
targets remain the public facade identities. No implementation DLL from an
upstream NuGet download is used as a build input or package payload.

The API gate checks 2,498 matching upstream public/protected signatures and
retains exactly three independently verified upstream reference/runtime
mismatches:

| Reference contract member missing from upstream runtime | Assembly |
| --- | --- |
| MtomMessageEncodingBindingElement.ReaderQuotas setter | Primitives |
| ReliableMessagingVersion protected parameterless constructor | Primitives |
| WSHttpBindingBase.EnvelopeVersion setter | Http |

The source contracts remain intact. The exact allowlist in
upstream-api-mismatches.json rejects additional missing members and stale
exceptions. The source implementation retains upstream behavior for these
three members. The evidence in [workflows/powershell-deps](https://github.com/Kreijstal/dotnet-mingw-bootstrap/tree/master/workflows/powershell-deps)/wcf-published-* was
obtained with PEReader/System.Reflection.Metadata, treating downloaded
published assemblies only as metadata. That audit never loads, executes or
compiles against the downloaded implementations. legacy-forwards.json records
only the shim's API forwarding table, not implementation code.

The clean build runs a bootstrap probe, generates facades and the shim, then
packs the seven NuGet packages. The check gate restores a fresh consumer from
the new feed plus installed source-built dependencies and checks:

- actual ChannelFactory/DispatchProxy/DataContractSerializer SOAP over HTTP;
- Unicode/action/body roundtrips through text, binary and MTOM encoders;
- WSDL reader/writer roundtrips;
- NetTcpBinding binary-session request/reply and session shutdown;
- DuplexChannelFactory callbacks over an actual NetTcp socket;
- BasicHttpsBinding over native TLS with custom certificate acceptance/rejection;
- all eight WCF assembly identities, source versions and consumer-local paths;
- all 274 legacy forwards resolving at runtime;
- all 26 rebuilt localized resource sets and 12,896 exact strings;
- absence of .NET Framework implementation modules;
- facade API signatures and exact method-free legacy forwarding metadata.

The protocol peers bind only private loopback TCP sockets. The HTTPS fixture
creates a temporary self-signed certificate and disposes its imported private
key container; no service, certificate store,
firewall or registry configuration is changed. The framed NetTcp fixture
follows the protocol documented in the pinned upstream FramingFormat.cs.
These tests do not establish all binary compatibility, generic constraints,
layout, interoperability, WS-Security, Windows authentication, federation,
remote WinRM or actual PowerShell integration.

NuGet emits NU5131 warnings for these explicit reference/runtime layouts, as
it does for the upstream facade layout. Installed-consumer checks verify actual
asset selection. Private's legacy source build emits 69 warnings, with no source
files excluded to hide errors.

Run a clean package build in CLANG64 with the listed source-built dependencies:

```bash
PATH=/usr/bin:/clang64/bin:$PATH makepkg --cleanbuild --force --noconfirm
```

After installing all seven packages, use a fresh output directory:

```bash
bash check-installed.sh /tmp/wcf-installed /clang64/share/doc/dotnet-private-servicemodel/localization.json
```

Validation records and package hashes are maintained under
[workflows/powershell-deps](https://github.com/Kreijstal/dotnet-mingw-bootstrap/tree/master/workflows/powershell-deps) in dotnet-mingw-bootstrap. The PowerShell dependency goal remains incomplete.
