# Original Roslyn 4.4 netstandard2.0 prerequisites

The original Standard2.0 compiler and C# Workspaces libraries are now formally
packaged and installed as `mingw-w64-clang-x86_64-dotnet-roslyn44 4.4.0-1`.
A complete clean build, installed-feed-only consumers, source/package audits
and existing-tool hash checks all exit 0. The package supplies four NuGets and
56 assemblies/satellites; validation covers all 11,932 listed APIs, 140 resource
sets / 39,900 strings, eight regenerated files and 3,799 original archive inputs.
Exact commands, attempt history, warnings and results are in
[package-results-20261028.txt](package-results-20261028.txt) and
[package-results-20261028.json](package-results-20261028.json).
The original netcoreapp3.1 variants and the broader dependency goal remain open.

The following records the earlier private build; its packaging status and
package-reference counts describe that historical run.

The subsequent [original .NET10 generator bundle](../runtime10-generators/README.md) now builds all six original shipping assemblies and passes generation/emit/source audits. That bundle remains private; formal packages and complete .NET10 integration are open.

Four private source packages now build and pass for the .NET10 JSON generator's
original Microsoft.CodeAnalysis.CSharp.Workspaces4.4 dependency: Common,
CSharp, Workspaces.Common and CSharp.Workspaces. Their production sources are
unchanged. These are private prerequisites; formal pacman packaging and the
complete .NET10 generator bundle remain open.

The pinned Roslyn commit is `1ce8866c9de4c2d67351ef6863699dee03b0804a`, archive
SHA256 `9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11`.
MSBuild evaluates the original netstandard2.0 projects in Release using their
original DotNetBuildFromSource switch. It selects all982 Common,1055 CSharp,
1430 Workspaces.Common and274 CSharp.Workspaces inputs. The supported original
SQLite exclusion is retained. Original resources, shared sources, expanded
friend identities, restricted namespaces, licenses and notices are preserved.

The declared older support-package minimums are recorded separately from the
actual source implementations used: runtime9 libraries, maintenance4.6.2 /
Unsafe6.1.1, Humanizer2.14.1 and the source .NETStandard2.0 contract. Package
metadata records the actual dependency versions used to compile; no dependency
assembly version or target is relabeled. No installed feed with duplicate IDs
is used for the Roslyn or Humanizer implementations.

Four unchanged original generator tools use20/3/1/4 C# files. Five CSharp and
three Core operation outputs match their pinned upstream files. The old
IOperation tool requires Debug: it advances an iterator inside Debug.Assert,
and the original generation script runs tools in Debug by default. The four
library packages remain Release. The canonical build.sh now selects this tool
mode. The successful producer resumed narrowly after the first Release tool
failure; exact individual commands are recorded, rather than claiming a fresh
successful whole-script run after that correction.

A fresh netstandard2.0 API consumer compiles and executes through the source
feed. Runtime checks cover C#11 required members/raw strings, parsing and
semantics, deterministic PE/portable PDBs and executed IL, syntax/type/nullable
and German diagnostics, analyzer loading/callbacks, incremental generation,
MEF Workspaces, Unicode documents, project references, cross-project reference
search/rename, formatting, simplification, DocumentEditor/code-fix actions,
incremental edits and cancellation. All11,932 listed APIs match. All140
resource sets /39,900 values match, including42 compiler sets /36,176 values
and all13 cultures. All96/28 Workspaces friend identities, restricted
namespaces and compiler identities pass. Five SDK-conflicted support assemblies
are explicitly checked to load from the source framework.

The old symbol display visitor renders IntPtr as nint against newer framework
metadata. The API checker renders only those native-integer type display parts
using their underlying CLR names, retaining all required declarations and
all other parameter/type/modifier information.

The audit verifies3,799 archive inputs,107 actual compiler/consumer package
references, every cached package/DLL, every copied Roslyn DLL/satellite, package
identity/dependencies, source commit and original licenses. The eight generated
output hashes are rechecked. These checks do not prove complete attribute
metadata, other framework groups or formal installation.

Copy this workflow into `roslyn44-ns20-workflow2` in the prepared CLANG64 root.
The pinned archive and existing source dependency feeds must be present.
Preparation and consumer directories must be new:

```sh
ROOT=/c/codex-dotnet10/c1.1BZ8KU
OUT="$ROOT/roslyn44-ns20-new"
WORK="$ROOT/roslyn44-ns20-workflow2"
/usr/bin/python3 "$WORK/prepare.py" "$ROOT" "$OUT"
bash "$WORK/build.sh" "$OUT"
/usr/bin/python3 "$WORK/check.py" "$ROOT" "$OUT" "$OUT/consumer"
/usr/bin/python3 "$WORK/audit.py" "$ROOT" "$OUT" "$OUT/consumer"
```

The validated output is `roslyn44-ns20-2/consumer6`. Exact successful producer,
consumer and audit commands, exit codes and complete logs are in
[source-results-20261028.txt](source-results-20261028.txt), with structured data
in [source-results-20261028.json](source-results-20261028.json).
All11 tested workflow files match the repository copies byte for byte.
Evidence: `/tmp/roslyn44-netstandard2/roslyn44-ns20-evidence2.tar.gz`, SHA256
`eeedacdf17d45de6f0b81ddec9c6b40e7f52a5d846b146d6f466892ebcab8a60`.

The next work is the original .NET10 generator projects, followed by formal
packages and installed validation. The broader PowerShell dependency goal is
incomplete. Installed package and catalog artifact counts are unchanged.
