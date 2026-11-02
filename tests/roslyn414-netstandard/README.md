# Original Roslyn 4.14 netstandard2.0 variants

The [formal compiler library recipe](../../mingw-w64-dotnet-roslyn414/README.md)
now builds and installs Common/CSharp4.14 Standard2.0 from a fresh source archive
using installed source prerequisites. Five regenerated compiler outputs, all
10,479 original public API declarations, all42 resource sets and fresh installed
consumer/source/cache/payload checks pass. See
[formal package results](package-results-20261028.txt). Workspaces, VB and other
required target variants remain part of the full goal. The records below describe
the earlier private bootstrap.

The latest validated output uses Release during original-project evaluation. Earlier output2 captured DEBUG constants before packing Release; it is superseded by output3. The corrected packages pass the full consumer and source audits, and the complete VB/meta-package consumer checks the original DEBUG-only member is absent. See [Release correction and validation](../roslyn414-visualbasic/source-results-20261028.txt).

Common and CSharp 4.14.0 now build for the original netstandard2.0 target with
unchanged production C# sources. They use the complete source-built
[runtime9 variants](../runtime9-netstandard/README.md),
[maintenance packages](../netstandard20-maintenance/README.md) and
[.NET Standard reference contract](../netstandard20-source/README.md).
These are private prerequisites; formal pacman packaging remains open.

The source revision is `8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b`, archive SHA256
`8cf2d365d1fad52b480f7c68b5c477cb586a935ada0eb309b0c40dacfec5fe9c`.
MSBuild evaluates the original projects and the source-build central versions
for netstandard2.0. The five previously regenerated original compiler source
outputs are reverified against their upstream baselines before every build.
All original resources and expanded friend declarations are retained.
The original CodePages7.0.0 dependency is a minimum; the actual resolved source
implementation/package/reference version is9.0.0 and is recorded as such.

The fresh consumer checks the declared library target and identity, a separately
compiled netstandard2.0 API consumer, C#13 spans/collection expressions, parsing
and semantics, deterministic PE/portable-PDB emit and execution, diagnostics,
cancellation, analyzer loading/callbacks and incremental source generation.
All4,242 Common and6,237 CSharp API declarations match. All42 resource sets,
39,956 values,13 cultures and German diagnostics pass.
Audits verify2,197 original source/API/resource/policy inputs and43 actual
compiler/consumer package references, including every cached DLL and both
packages' original license/notices bytes.

Copy this directory to `roslyn414-ns20-workflow` in the prepared Windows CLANG64
root. The preceding `roslyn414-1` extraction/generated outputs and source feeds
are prerequisites. Preparation and consumer output directories must be new:

```sh
ROOT=/c/codex-dotnet10/c1.1BZ8KU
/usr/bin/python3 "$ROOT/roslyn414-ns20-workflow/prepare.py" "$ROOT" "$ROOT/roslyn414-ns20-3"
bash "$ROOT/roslyn414-ns20-workflow/build.sh" "$ROOT" "$ROOT/roslyn414-ns20-3"
/usr/bin/python3 "$ROOT/roslyn414-ns20-workflow/check.py" "$ROOT" "$ROOT/roslyn414-ns20-3" "$ROOT/roslyn414-ns20-3/consumer1"
/usr/bin/python3 "$ROOT/roslyn414-ns20-workflow/audit.py" "$ROOT" "$ROOT/roslyn414-ns20-3" "$ROOT/roslyn414-ns20-3/consumer1"
```

All final commands returned zero. `check.py --resume` explicitly reuses a consumer.
Latest commands and hashes are in [the Release/VB record](../roslyn414-visualbasic/source-results-20261028.txt). The [earlier JSON record](source-results-20261028.json) and [logs](source-results-20261028.txt) retain output2 history. The subsequent
[Workspaces variants](../workspaces414-netstandard/README.md) use these packages.
The complete generator bundle, original4.4 JSON dependencies, full package
metadata/attribute/target/install gates and framework/SDK/desktop10/PowerShell7.6
closure remain open. Established dependency artifact counts are unchanged.
