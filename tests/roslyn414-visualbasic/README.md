# Roslyn 4.14 Visual Basic and complete meta-package prerequisites

The original Standard2.0 VB compiler, VisualBasic.Workspaces and both-language
metapackage are now formally packaged and installed as
`mingw-w64-clang-x86_64-dotnet-roslyn414-visualbasic 4.14.0-1`.
The clean package build, fresh installed consumer, source audit, installed byte
audit and existing-tool hash checks all exit 0. This verifies 6,096 compiler API
declarations, 49 MEF exports, 42 language services, 1,225 original archive inputs,
three NuGets and 28 assemblies/satellites. Exact commands and results are in
[package-results-20261028.txt](package-results-20261028.txt) and
[package-results-20261028.json](package-results-20261028.json).
Original NET8/NET9 variants and the full dependency goal remain open.

The following records the earlier private builds; its packaging status and
package-reference counts describe those historical runs.

The subsequent [original .NET10 generator bundle](../runtime10-generators/README.md) now builds all six original shipping assemblies and passes generation/emit/source audits. That bundle remains private; formal packages and complete .NET10 integration are open.

Three private netstandard2.0 packages now build from unchanged original Roslyn
4.14 sources: VisualBasic, VisualBasic.Workspaces and the Microsoft.CodeAnalysis
meta package. The meta package retains both original language Workspaces
dependencies. This closes the VB branch declared by the .NET 10 interop
source-generation project. Formal pacman packaging remains open.

The pinned source commit is `8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b`, archive
SHA256 `8cf2d365d1fad52b480f7c68b5c477cb586a935ada0eb309b0c40dacfec5fe9c`.
The compiler uses 909 original VB inputs, five regenerated original VB files,
and all four embedded source templates. Three original generator tools use
17 VB, one VB and three C# inputs; their five outputs and grammar match
upstream. Workspaces uses all 235 original VB inputs and original shared imports.

This build exposed a configuration mismatch in the earlier private C# variants:
MSBuild evaluated their constants with the default Debug configuration, then
packed with Release. The updated preparation scripts select Release during
evaluation and reject DEBUG constants. Common, CSharp, Workspaces.Common and
CSharp.Workspaces were rebuilt in new outputs and passed their complete
existing consumer/source audits. A runtime regression check verifies that
Common's DEBUG-only abstract message-provider member is absent.

The original Arcade SDK policy is pinned by Roslyn's Version.Details.xml to
commit `1cfa39f82d00b3659a3d367bc344241946e10681`. Preparation verifies the
source archive (`f3de8289da570f5c1ce269163e8b25ef12062a4a6dc9620d2bd16c1aba3c3f59`)
and the original ProjectDefaults.props. Every VB wrapper preserves MyType=Empty,
OptionCompare=Binary, OptionStrict=On and RemoveIntegerChecks=true. The original
syntax generator explicitly overrides strict mode to Off. The final output4
rebuild and consumer pass with those defaults; the policy audit checks each
wrapper. The pinned archive must be present in the prepared root as
`arcade-roslyn414-1cfa39f8.tar.gz`. It is available locally at `/tmp/arcade-roslyn414-1cfa39f8.tar.gz`.

The fresh consumer restores the full meta package from source-only feeds. It
checks 6,096 listed VB APIs, 14 compiler resource sets / 25,312 values, 42
Workspaces resource sets / 700 values, four embedded templates and original
friend identities. All 49 MEF exports activate and all 42 language services /
factories resolve. Cross-language references/rename, formatting, simplification,
code actions, document editing, cancellation, compiler/analyzer/generator
callbacks and actual emitted-code execution pass. The original project has
29 compiler friend declarations, including a duplicate: all 28 unique emitted
identities are verified, along with all 19 Workspaces identities.

The source/package audit verifies 1,225 archive inputs and 85 actual compiler /
consumer package references, every cached package and DLL, and the consumer's
exact six Roslyn DLL/resource sets against their source packages. Meta-package
identity, two declared dependencies, original licenses and source commit pass.
The corresponding corrected C# audits verify 2,197 / 1,894 archive inputs and
43 / 66 actual package references. These checks do not establish complete
attribute metadata or formal package installation.

Exact commands, exit codes, package hashes and logs are in
[source-results-20261028.txt](source-results-20261028.txt), with structured data
in [source-results-20261028.json](source-results-20261028.json).
The local evidence archive is `/tmp/roslyn414-release-vb4/roslyn414-release-vb-evidence4.tar.gz`,
SHA256 `073e1aa47e0d3c7ad45ddfc4c24ed28d568eb22542dbdbf390ce2890e0cc6345`.
All 30 tested workflow and pinned policy/license files match the repository copies byte for byte.

The next missing generator prerequisite is Roslyn/Workspaces 4.4 for JSON.
The complete .NET 10 generator bundle, formal packages and installed checks
remain open. No package-catalog count or installed package changed.
