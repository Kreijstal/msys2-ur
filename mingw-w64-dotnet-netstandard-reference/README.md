# Source .NET Standard reference package

Builds the complete original .NET Standard 2.0 contract and facade graph from
dotnet/standard commit `18a36291e48808fa7ef2d00a764ceb1ec95645a5` with the declared,
installed source Compiler5 bootstrap host. No private build roots or vendor
assemblies are used. All 117 assemblies compile from unchanged original C#;
113 original reference assets ship in the pack and NuGet. Four extension
references are build prerequisites and remain outside the package payload.

The NuGet retains all 20 original publisher dependency groups, 337 edges and 44
unique dependency versions. The pinned publisher nuspec is metadata only; all
dependency versions are checked against the original source baseline. Original
targets and the netstandard1.0 placeholder layout are retained. Assembly versions,
keys, original reference/facade markers, dependency identities and 4,197 original
type forwards are validated against the source graph. The 112 facade assemblies
retain the original runtime-loadable policy from `netstandard/pkg/shims/dir.targets`.
All are actually loaded, three representative type forwards execute, and the
reference-only core contract must be rejected by the CLR. Facade file versions
retain the original 4.6 major/minor policy and use 4.6.26419.0 from the pinned
source date and original BuildTools date formula. The core and four extension
reference files use bootstrap file version 2.0.3.0.

All 117 files retain the original `CLSCompliant(true)` default from BuildTools
`Build.Common.targets`, applied before its later versioning defaults. This is
checked from the pinned original policy and every emitted assembly. Revision3
corrects the omitted CLS marker in the preceding bootstrap/reference packages.

Public-key provenance, including the original BuildTools Silverlight key
mapping, is pinned in `inputs/key-provenance.json`.

Run `python make-source.py`, then in Windows CLANG64 run
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
The check builds a fresh netstandard2.0 SDK consumer using only source feeds,
verifies all 113 actual compiler references, executes async Unicode, LINQ,
collections and tuple behavior on the source runtime, and rejects a newer API.

After installing the package, repeat `check.py ARCHIVE BUILT NEW_CONSUMER
/clang64/lib/dotnet/library-packs` from the source workflow. This validates an
empty restore cache, installed NuGet bytes and every installed reference DLL.

The package installs under `lib/dotnet/packs/NETStandard.Library.Ref/2.0.3` and
adds `netstandard.library.2.0.3.nupkg` to the source feed. Older framework dependency
groups are preserved; their complete runtime dependency closures are not yet
validated. The full PowerShell dependency goal, complete generator package graph
and .NET10 SDK/runtime integration remain open.
