# Source .NET Standard 2.0 reference prerequisite

This is a historical bootstrap workflow. Its reference-only marker on every
assembly differs from the original shim runtime-loading policy. The formal
[reference package](../../mingw-w64-dotnet-netstandard-reference/README.md)
retains reference-only markers for the core contract and extension inputs while
building the 112 facades as runtime-loadable assemblies with the original 4.6
file-version policy. Use that recipe for new builds; the records below describe
the earlier bootstrap profile.

The latest [revision3 validation](package3-results-20261028.txt) also restores the
original BuildTools CLS-compliance default on all117 assemblies. Their source
compilations now produce zero compiler warnings.

The original .NET 10 shipping generators target `netstandard2.0`. The preceding
[Workspaces bootstrap](../runtime10-workspaces414/README.md) builds the original
supported net8 variants. This workflow supplies the older reference contract
needed to build the declared shipping variants and their dependencies.

Source: dotnet/standard commit `18a36291e48808fa7ef2d00a764ceb1ec95645a5`,
declared by [NETStandard.Library 2.0.3](https://www.nuget.org/packages/NETStandard.Library/2.0.3).
The source archive SHA256 is
`754ee66a33122c6c5c45fe75d060f9131c6b16a23af315c8c063a54fbc911e7c`.
No production C# inputs are edited. Archived binary inputs are removed and
recorded before compilation.

`build.py` reads the original projects and their dependency graph. It compiles
the complete netstandard reference contract, 112 original facade projects and
four extension reference projects used by the facade build. It retains original
assembly names, assembly versions, public keys and type-forwarding sources.
The private wrapper generates assembly metadata with bootstrap file version
2.0.3.0. Public signing uses the source bootstrap's public keys; the uncommon
SilverlightExtension mapping and exact public key are independently checked
against the original BuildTools signing definitions. See
[`inputs/key-provenance.json`](inputs/key-provenance.json).

`check.py` verifies every selected production source/project against the pinned
archive, all 117 output hashes, identities, keys, reference markers, dependency
identities and every original facade forward. It creates a private NuGet
containing the original targets template and all 113 netstandard2.0 reference
assets. The four extension reference inputs remain outside that package, as
specified by the original package project.

A fresh SDK consumer targets netstandard2.0, restores solely from source feeds
and records its actual compiler references. Its async Unicode, collections,
LINQ and tuple code runs on the source .NET 8 runtime. A negative compile check
requires a newer framework API that the older contract must reject.

Copy this directory to `netstandard20-workflow` in the prepared Windows CLANG64
root and place `standard-18a36291.tar.gz` beside it. The source SDK8 and unchanged
source Roslyn5 compiler adapter must already be present. Output and consumer
directories must be new:

```sh
ROOT=/c/codex-dotnet10/c1.1BZ8KU
/usr/bin/python3 "$ROOT/netstandard20-workflow/build.py" "$ROOT" "$ROOT/netstandard20-2"
/usr/bin/python3 "$ROOT/netstandard20-workflow/check.py" "$ROOT" "$ROOT/netstandard20-2" "$ROOT/netstandard20-2/consumer3"
```

Both recorded commands returned zero. All 250 original source/project inputs,
4,197 forwarded types and 113 actual consumer reference paths pass. The core
contract has 2,418 type definitions and 24,177 method definitions. The compiler
reports 453 nonfatal CS3021 warnings about member CLS attributes without an
assembly CLS marker in the private wrapper. Restore retains the original
Platforms >=1.1.0 minimum and reports NU1603 while selecting the available source
1.1.2 package. The consumer cache archives and reference bytes match the source
feeds. Detailed hashes and logs are in
[the JSON record](source-results-20261028.json) and
[the text evidence](source-results-20261028.txt).

This is a private reference prerequisite for the netstandard2.0 generator
closure. Earlier .NET Standard 1.x package dependency groups, a formal complete
NETStandard.Library pacman package, the shipping generator bundle and the full
PowerShell dependency objective remain open.

The subsequent [maintenance dependency build](../netstandard20-maintenance/README.md)
uses these references for five original netstandard2.0 implementations, including
Unsafe from original IL with the native source .NET 10 assembler.
