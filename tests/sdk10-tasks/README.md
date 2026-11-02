# SDK10 build-task bootstrap

Builds the original source-only NET10 profiles of Microsoft.NET.Build.Tasks,
Microsoft.NET.Build.Extensions.Tasks, Microsoft.DotNet.ApiCompat.Task,
Microsoft.DotNet.ApiCompatibility, Microsoft.DotNet.ApiSymbolExtensions and
Microsoft.DotNet.PackageValidation from the pinned SDK10.0.201 archive.
All299 original Compile items are preserved, including linked source and the
APICompat `unused` reference alias and Extensions build-only project edge.
No original production C# is patched. Original source policies select NET10;
additional original NET472 profiles remain required.

The original Arcade resource/version tasks run in a standalone source SDK8
helper host. The explicit bootstrap BuildID20260213.113 follows the original
version formula and is recorded separately from published SDK metadata.
The SDK tag defaults to VersionPrefix10.0.200: APICompat assemblies therefore
have assembly10.0.200.0/file10.2.26.11413; task assemblies use original automatic
assembly version10.0.14.11413. This package does not assert published task
assembly identity. Strong-name key policies and all78 language satellites,
112 neutral/localized resource sets and six portable PDB associations are checked.

The package installs under
`lib/dotnet10/build-packs/sdk-10.0.201-net10-bootstrap`. The bin directory
includes source-built dependency assets whose source archive/member/hash or
installed source path is recorded. MSBuild APIs stay in the source MSBuild18
host. Original task targets/props/content are retained under original-content
with their source paths. The archive/source/resource/reference/output audit is
part of check(). All restored/compiler/runtime implementations are installed
source packages; no published implementation assemblies are downloaded.

The installed check executes the original RuntimeConfiguration/CreateAppHost
and Extensions facade tasks through source MSBuild18, executes a Unicode NET10
native app, accepts a compatible API pair and requires CP0002 for a removed
member. It verifies exact resources, assembly/file/key/framework identity,
portable PDBs and payload hashes:

```sh
/clang64/bin/python.exe -X utf8 \
  /clang64/share/doc/dotnet-sdk10-tasks-bootstrap/checks/check-installed.py \
  E:/msys64/clang64 NEW_OUTPUT
```

This is one SDK bootstrap component. A complete SDK layout/driver, original
Arcade/analyzer integration, formal exact MSBuild NuGet archives, NuGet
restore/build/pack tasks/resolver, NET472 profiles, NETStandard.Library.NETFramework
content, full upstream suites and broader task behavior remain open. Full
SDK10/desktop10/PowerShell7.6 and the earlier native/framework compatibility gates
are still required. This package does not complete the dependency-porting goal.

The clean package build and installed check passed on win11 on 2026-10-29.
`makepkg --cleanbuild --force --noconfirm` exited 0. The archive audit maps
all 312 binary/symbol/documentation assets to source outputs or dependencies;
533 payload hashes match. Pacman reports 629 files and zero altered files.
The installed checks passed all 7,672 resource values, original task execution,
the expected APICompat CP0002 rejection and native NET10 Unicode/argument checks.
Exact commands and results: [package-results-20261029.txt](package-results-20261029.txt).
Archive provenance: [package-artifact-20261029.json](package-artifact-20261029.json).
