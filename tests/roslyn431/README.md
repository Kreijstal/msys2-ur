# Roslyn 4.3.1 NS2 prerequisite for PolySharp

Builds Microsoft.CodeAnalysis.Common and Microsoft.CodeAnalysis.CSharp 4.3.1
from original commit 4bdc8414790101a4da120a92cc4bc0154ac787ca. These are the
exact compiler-library versions declared by PolySharp 1.15.0. Both retain their
original netstandard2.0 profile, assembly 4.3.0.0, Microsoft public signing key,
source feature guards and friend declarations. No production C# is edited.
The bootstrap file version is explicitly 4.3.0.0; informational version records
4.3.1 plus the full source commit.

The source-built compiler 5.0 runs on source runtime 8.0.31 with source SDK
8.0.131. Four original generator tools run on NET8 (the IOperation tool in
its original manual-generation Debug mode). All eight regenerated files must
match their original baselines after the recorded upstream console cleanup.
The bootstrap uses installed source support libraries: Immutable/Metadata 9,
CodePages 9, Memory 4.6.2, Unsafe 6.1.1 and Tasks.Extensions 4.6.2, with exact
resolved versions recorded separately from the original minimum requirements.
These are bootstrap dependency versions, not claims of original release parity.

The build replays the pinned source's C# strict/nullable/warning policy.
Imports.targets suppresses nullable warnings for the older profile of an
original multi-targeted project; the NS2 branch preserves that original policy.
Warnings-as-errors remains enabled. Source-build analyzer exclusions are retained.
The original NETCoreApp3.1 profile and full upstream test/toolchain matrix remain
unverified; this package supplies the NS2 prerequisite for the dependency port.

Validation builds fresh NS2 and NET8 consumers from the source-only feeds,
checks original public API declarations, signing/version/friend identities,
all resource sets, C# preview required members/raw strings, diagnostics,
analyzer loading, incremental generators, deterministic emit and portable PDBs.
The archive audit compares actual compiler inputs and cached/copied DLL bytes
with the pinned source and produced NuGet packages. The broader PowerShell
dependency goal remains open.
