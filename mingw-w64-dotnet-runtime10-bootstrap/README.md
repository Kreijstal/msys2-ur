# Source-built .NET 10 runtime bootstrap

Builds the complete original runtime 10.0.5 managed implementation graph from
the pinned source archive: 171 shipping managed assemblies, 19 private facade
seeds and the separately source-built CoreLib. The private seeds are not shipped.
The installed source host, CoreCLR, CoreLib and native compression/globalization
components supply an isolated, 172-assembly shared framework under
`lib/dotnet10`. The `dotnet10-bootstrap` command selects this runtime with
process-local environment settings.

The build runs the original resource, ASN.1, facade, unsupported-platform,
versioning and library-link tasks. Source compiler and task hosts use explicit
NET8 bootstrap profiles. Public APIs, resources, forwarders, symbols and original
source hashes are checked. Full-layout probes exercise new collections, JSON,
XML, VB, regular expressions, Reflection.Emit, cryptography, Unicode async file
I/O, local HTTP, compression, globalization and JavaScript's original Windows
unsupported-platform behavior. The same probes run through the real source
dotnet host before packaging and after installation.

The strict reference-contract comparison is retained, including its nonzero
exit status. The prototype has zero missing declarations but extra declarations
and changed shapes remain under review. Packaging this bootstrap does not certify
strict contract parity or complete runtime compatibility. Reports are installed
under `share/doc/dotnet-runtime10-bootstrap`.

This package does not supply SDK10 or PowerShell7.6. Original NET10 compiler/tool
profiles, MsQuic/QUIC, browser execution, COM, debugger/DAC, R2R/AOT, desktop and
the other outstanding PowerShell compatibility gates remain open. This is a
step toward the full dependency graph, not completion of that goal.

From the repository, export the frozen workflow with:

```sh
python3 mingw-w64-dotnet-runtime10-bootstrap/make-source.py --update-checksum
```

Then run `makepkg --cleanbuild --force --noconfirm` from this recipe in CLANG64.
Validate the installed files with:

```sh
/usr/bin/python3 /clang64/share/doc/dotnet-runtime10-bootstrap/checks/check-installed.py \
  /clang64 NEW_OUTPUT
```
