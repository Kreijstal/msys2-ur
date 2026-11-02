Original System.Formats.Asn1 8.0.1 .NET 8 source profile, from runtime 8.0.7
commit 2aade6beb02ea367fd97c4070a4198802fe61c03. It retains the Open key,
assembly version 8.0.0.0, file version 8.0.724.31311 and original compiler policy.

Build in MSYS2 CLANG64:

```bash
makepkg --cleanbuild --force --noconfirm
```

The source snapshot has 4,418 original files and excludes binary fixtures.
Source Csc 5.3 on .NET 10 compiles against source .NET 8 references. The
original Arcade 8 version/resource tasks run on the source SDK 8 host.
Documentation follows original eng/intellisense.targets and the pinned
Microsoft.Private.Intellisense 8.0.0-preview-20230918.1 XML. Its exact bytes
match the published .NET 8 package XML; no published assembly is compiled
against or executed.

Checks cover 43 original inputs, 213 CLR/nullable API entries, 34 resource
values, portable PDBs and exact produced/cached DLL execution on source
.NET 8 and .NET 10. The installed gate restores offline using source NuGet 7.3
with warnings-as-errors. Original additional framework profiles, full upstream
suites and the overall PowerShell dependency goal remain open.

[Source and prototype evidence](../tests/asn1801/prototype-results-20261031.txt).

The clean build, final archive audit, installation and fresh installed gate
passed. Pacman reports 49 files and zero alterations. Existing ASN.1 8.0.2 and
10.0.2 archives and the .NET 8 framework reference retain their hashes.
[Exact commands and results](../tests/asn1801/package-results-20261031.txt).
