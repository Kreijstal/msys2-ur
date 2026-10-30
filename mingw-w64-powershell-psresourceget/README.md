# PSResourceGet 1.1.1 from source

The recipe builds the complete original project at commit
`44697aed1740126153a8d9dd0ef368261b2fe45c`: all56 production C# files and all six
original module assets. A.NET8 wrapper imports the original project and references
the complete installed source PowerShell7.4.20 engine, exact source NuGet6.9.1,
JSON8.0.5 and Azure.Identity1.11.4 dependencies. Original Http/CSharp/Web framework
references use the source framework; PowerShellStandard's API stub is replaced by
the actual source engine. Original assembly/file1.1.0.1 and informational commit
remain. This build requires a.NET8 PowerShell host; the unchanged original manifest's
Desktop compatibility fields describe the upstream release, not this retargeted build.

One exact source overlay qualifies a SortedDictionary constructor's SemanticVersion
as NuGet.Versioning.SemanticVersion. The original return and variable types already
say NuGet; modern SMA additionally exposes a conflicting SemanticVersion type.
The original archive is unchanged,55 inputs compile unchanged and the qualification
overlay is hashed and shipped separately. The original build retains243
XML-documentation/nullability/value-comparison warnings.

The native package installs the complete loose module under
`$MINGW_PREFIX/lib/powershell/Modules/Microsoft.PowerShell.PSResourceGet/1.1.1` and its
PSModule NuGet archive in the source-built feed. All26 private DLLs match the exact
installed source-built NuGet runtime assets; their license files and nuspecs are
included. Windows RID-specific PKCS is selected from the original runtime asset
alongside the25 general runtime libraries. The package also retains the compiler/reference inventory, exact overlay
and wrapper projects, reference assembly, XML docs and original MIT license/notices.
It does not package a vendor implementation or the host's SMA assembly.

The source-engine check imports all17cmdlets and the nested script module, exercises
new/get/test/update script metadata and verifies loaded private NuGet paths/hashes.
An actual source test cmdlet invokes the original ACR version-selection helper,
checking the qualified key type, numeric ordering, stable/prerelease ranges,
normalized exact matching and invalid-version errors without a registry request.
All460 published public/protected APIs and release identities are checked using
metadata inspection. The vendor.NETFramework baseline was interpreted with matching
Framework metadata references; Framework implementations are never production
references or runtime inputs.

The local lifecycle check creates uniquely owned repository and module names. It
checks repository get/register/set, publish/find, required-dependency save/install,
NuGet archive save, installed metadata/update, Unicode module execution, uninstall
and missing-package errors. Only those owned repository entries and module paths
are removed; existing repository entries are checked for preservation. The source
repository store uses Windows LocalApplicationData and CurrentUser installations use
MyDocuments. Process environment redirection does not isolate these special folders.
The fixture restores its process module path and does not overwrite the repository
store or change policy, persistent PATH, trust stores or registry settings.

Build with `makepkg --cleanbuild --force --noconfirm` in MSYS2 CLANG64. After
installation, validate a fresh restored, relocated and installed loose module with:

```bash
bash check.sh NEW_OUTPUT $MINGW_PREFIX/lib/dotnet/library-packs \
  $MINGW_PREFIX/lib/powershell/Modules/Microsoft.PowerShell.PSResourceGet/1.1.1
```

The runtime reports.NET8.0.0; runtime servicing, authenticated remote repositories,
ACR/Azure service integration, network publishing, broad policy behavior and the
complete shipping PowerShell application remain separate verification work.
