# Original Workspaces 4.14 netstandard2.0 variants

The [formal Workspaces recipe](../../mingw-w64-dotnet-roslyn414-workspaces/README.md)
now builds and installs both Standard2.0 libraries using installed source
prerequisites. Fresh installed consumers pass all1,890 original API declarations,
98 resource sets, friend/restricted namespace checks and MEF/refactoring/code
action/Channels behavior. See [formal package results](package-results-20261028.txt).
The records below describe the earlier private bootstrap; VB and other required
target variants remain part of the full dependency goal.

The latest validated output uses Release during original-project evaluation. Earlier output2 captured DEBUG constants before packing Release; it is superseded by output3. The corrected packages pass the full consumer and source audits, and the complete VB/meta-package consumer checks the original DEBUG-only member is absent. See [Release correction and validation](../roslyn414-visualbasic/source-results-20261028.txt).

Workspaces.Common and CSharp.Workspaces4.14 now build for netstandard2.0 with
all1,515 and271 original C# inputs unchanged. They use the source
[Roslyn4.14](../roslyn414-netstandard/README.md),
[Humanizer](../humanizer-netstandard/README.md) and
[runtime9](../runtime9-netstandard/README.md) variants. The original source-build
SQLite exclusion remains in effect. The original Channels7 minimum resolves to
the complete source9 implementation with its actual identity/dependency version.

The original Roslyn commit is `8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b`, archive
SHA256 `8cf2d365d1fad52b480f7c68b5c477cb586a935ada0eb309b0c40dacfec5fe9c`.
MSBuild evaluates the original target conditions and central package versions.
The private wrappers retain all resources and expanded friend declarations and
ship the original license/notices text.

A fresh source-only consumer checks all1,834 Common and56 CSharp API declarations,
104 and29 friend identities, restricted namespaces and98 resource sets/3,486
strings. Behavior checks cover real MEF composition, Unicode documents, project
references/semantic models, cross-project reference search/rename, formatting,
simplification, solution changes, PE emit, analyzer diagnostics, DocumentEditor,
code-fix registration, CodeAction/ApplyChanges, incremental edits and cancellation.
The source9 Channels lifetime/backpressure/multiwriter/error checks pass too.

The verifier checks every cached package/DLL and the assets in the final `.deps`
runtime manifest. SDK conflict resolution replaces five older support assemblies
with the source .NET8 framework providers; those five actual loaded locations are
checked explicitly. Their package caches are still checked in full.
The separate provenance audit verifies original source/API/resource inputs,
package dependencies, licenses and actual compiler/consumer caches.

Copy this workflow to `workspaces414-ns20-workflow` in the prepared Windows
CLANG64 root. The preceding source feeds and the original `workspaces414-1`
wrapper/resource baseline are prerequisites. Preparation and consumer directories
must be new:

```sh
ROOT=/c/codex-dotnet10/c1.1BZ8KU
/usr/bin/python3 "$ROOT/workspaces414-ns20-workflow/prepare.py" "$ROOT" "$ROOT/workspaces414-ns20-3"
bash "$ROOT/workspaces414-ns20-workflow/build.sh" "$ROOT/workspaces414-ns20-3"
/usr/bin/python3 "$ROOT/workspaces414-ns20-workflow/check.py" "$ROOT" "$ROOT/workspaces414-ns20-3" "$ROOT/workspaces414-ns20-3/consumer1"
/usr/bin/python3 "$ROOT/workspaces414-ns20-workflow/audit.py" "$ROOT" "$ROOT/workspaces414-ns20-3" "$ROOT/workspaces414-ns20-3/consumer1"
```

All final commands returned zero. `check.py --resume` explicitly reuses a consumer.
Latest commands and hashes are in [the Release/VB record](../roslyn414-visualbasic/source-results-20261028.txt). The [earlier JSON record](source-results-20261028.json) and [logs](source-results-20261028.txt) retain output2 history.
The original4.4 JSON dependency closure, complete runtime10 generator bundle,
formal package metadata/attribute/target/clean/install gates and full framework/
SDK/desktop10/PowerShell7.6 closure remain open. These private package variants
do not increase the established dependency artifact counts.
