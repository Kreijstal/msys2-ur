# Microsoft.PowerShell.Archive1.2.6 from source

The source is PowerShell/Microsoft.PowerShell.Archive servicing commit
87428e309898a728fb0287eab31b5cd214ceb9ba, archive SHA256
85abf447302a2a6cc938212053d5b6b91fb20e9204062db60d8f63f46bb24822.
The module manifest, implementation and English resource source match the
published1.2.6 source after excluding BOM/line-ending/signing material. The Gallery
package is used only for independent source comparison, never as production input.

The package ships the full original script module, manifest and en-US data, with
one correction: add the new reserved-device warning to the inline fallback
dictionary as well as the English resource file. Upstream's inline dictionary
omits it, producing an empty warning when Import-LocalizedData cannot find an
en-GB/parent resource. Compression/extraction algorithms are unchanged. The PSM1
is normalized to LF/UTF8 for the explicit zero-fuzz patch. Manifest/resource bytes
remain unchanged. Source scripts are unsigned; no vendor signing block is copied.

The dependency-free NuGet PSModule is installed in the source-built library feed.
The same source files are installed under lib/powershell/Modules/
Microsoft.PowerShell.Archive/1.2.6 for an explicit PowerShell module import. This
module is a dependency of the forthcoming full PowerShell application.

Checks restore the exact package into an empty cache with only source-built
feeds. The complete original Pester suite runs against the restored module in
en-GB and en-US. Original fresh PowerShell sessions discover byte-identical module
copies. Two explicit fixture changes retain the original test bodies: use an owned
TestDrive root instead of creating/deleting the fixed system-drive SourceDir,
and restore a missing comma so all31 intended reserved-device cases execute.
Each culture run requires99 total cases,98 passed, no failures/skips and the one
upstream pending non-English-import test. The explicit en-GB run also exercises
fallback localization without changing the upstream pending marker.

The source-built module test host includes the original PowerShell engine and
stock command projects, source Pester4.10.1/Gherkin, source reference metadata and
Add-Type. No published PowerShell or Framework implementation is used.

```bash
makepkg --cleanbuild --force --noconfirm
pacman -U mingw-w64-clang-x86_64-powershell-archive-1.2.6-1-any.pkg.tar.zst
bash check.sh NEW_OUTPUT /path/to/pinned-archive-source
```

Archive's two exported functions retain version1.2.6 and original module GUID
eb74e8da-9ae2-482a-a648-e96550fb8733. This package does not complete the remaining
PowerShell application, modules, native ports or.NET runtime servicing work.
