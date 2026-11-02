# Original Roslyn 3.4 source bootstrap

The original Common and CSharp libraries build at `netstandard2.0` from commit
`82f2e2541478e239dc4b04f231e90dc2b3dcb422`. The strict final build uses the
source-built original 3.4 compiler, C# 8, warnings as errors, and the exact
historical source-built support dependencies. All 1,670 selected C# inputs
match the source archive. Original checked-in generated C# files are included;
the historical generator/Arcade workflow has not yet been replayed.

The audit matches all 11,106 public API entries, assembly identities, assembly
attributes, and dependency identities. Both neutral assemblies and all 26
localized satellites preserve 29,008 original resource strings, the embedded
manifest, and native version information. Both generated XML documentation
files are byte-identical to the published assets. Fresh portable PDBs accompany
the source builds; original PDB byte equality is not claimed.

`prepare.py` preserves MSBuild's default glob order followed by the original
shared imports. That order matters to an original per-file CS0660 pragma on
partial TypeSymbol declarations. Raw source files remain unchanged. Separate
CRLF resource projections reproduce Windows checkout behavior under the
original `.gitattributes`; published resource baselines are compared unchanged.

The initial Roslyn 4.4 seed reports 437 newer nullable warnings and is excluded
from the strict final result. `bootstrap.py` combines three unchanged original
local CLI files with two explicit NET8 bootstrap ports. The isolated driver
enforces requested dependency versions. Its encoding registration resolves
the CodePages identity referenced by the original Common assembly. The final
compiler checks cover C# 8 parsing/emission/execution, Shift-JIS source decoding,
and expected nullable, language-version, and syntax failures.

Published assemblies are inspected through PE metadata/resource readers and
FileVersionInfo. They are never executed or used as compiler references.
Public signing preserves the original assembly public-key identity; it does
not reproduce Microsoft's private-key signatures.

The exact commands, retained failures, final results, hashes and remote roots
are recorded in [prototype-results-20261031.json](prototype-results-20261031.json)
and [the command log](prototype-results-20261031.txt).

This is a source-bootstrap milestone. No Roslyn 3.4 package has been installed.
Original Microsoft.CodeAnalysis.Analyzers 2.9.6 packaging remains necessary for
the published Common dependency group. The full Toolset still requires its
original net472/netcoreapp2.1 executables, VB, scripting, compiler server,
MSBuild tasks, native DiaSymReader payloads, and complete original build
workflow. ReferenceAssemblyAnnotator alpha160 and the full PowerShell
dependency goal remain incomplete. The original asset requirements are pinned
in [the profile inventory](original-profile-requirements-20261031.json).
