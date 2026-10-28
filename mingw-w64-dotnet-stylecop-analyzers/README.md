# StyleCop.Analyzers 1.2.0-beta.556 source packages

Two packages retain the full upstream analyzers and code fixes for PowerShell's
requested version: `StyleCop.Analyzers` 1.2.0-beta.556 is the dependency-only
package; `StyleCop.Analyzers.Unstable` 1.2.0.556 contains both source-built
assemblies and all seven satellite cultures. The meta-package pins the exact
implementation version. Packaging and installed checks use only source-built
Roslyn 4.9.2, Workspaces and the installed csc49 compiler host.

Source is pinned to commit `73a46ae2e65e7870fefe35e2c4c12bb7152f4ec5`, Git tree
`c825926498b59694e7f559cd6d55377bbac57283`. The archive and Git endpoints were
unavailable during this run. All 2,811 files were retrieved from the official
raw GitHub endpoint and checked against their Git blob hashes. Every Git tree
and the original signed commit were reconstructed; `git fsck --strict` passed.
`verify-source.py` independently verifies the complete source tree and original
commit without relying on the download process. It uses the eight executable
file modes recorded in `source-inputs.json`, including when checking on Windows.

The port builds the complete seven-file upstream generator, 313 analyzer source
files and 107 code-fix source files for .NET 8. It regenerates all 183 upstream
light-up output files using the source-built Roslyn 4.9.2 compiler host. The
checked-in preview output under `Lightup/.generated` is excluded from Compile,
matching the upstream SDK's hidden-directory exclusion.

The syntax generator retains the 57 wrapper types recorded in the pinned source.
Newer compiler references would otherwise suppress types still used by partial
wrappers and `SyntaxFactoryEx`. The regeneration gate checks 179 outputs with
identical C# tokens, plus four outputs with six precise adaptations where newer
Roslyn exposes real `AttributeLists`/`Modifiers` properties in place of the old
reflection extensions. Formatting trivia differs with the newer compiler.
Code fixes explicitly bind the original StyleCop `DocumentBasedFixAllProvider`
and two original `SpacingExtensions.WithoutTrivia` calls, avoiding collisions
with newer Roslyn APIs. No rule or code-fix implementation is removed. A further SA1134 port guard
preserves the original invalid-syntax behavior: newer Roslyn can recover a
malformed attribute as an AttributeListSyntax. Both incremental and Fix All
paths skip attribute lists containing syntax diagnostics, rather than rewriting
malformed user code. The original upstream regression case checks this guard.

All ten neutral resource wrappers are generated from original resx files. All
17 resource sets and seven satellite cultures are retained. The original public
identity is public-signed using only the public component derived from the
checked-in development key; private key data is not a shipping artifact.
The target is assembly `1.2.0.556`, token `cfeb5dbada5e1c25`.

The independent published baseline contains 182 analyzer classes, 89 exported
code-fix providers and 178 DiagnosticId constants. Published assemblies were
read only as PE metadata; they are never executed, referenced or packaged.
The checks validate all classes, 197 live descriptors, all 17 resource sets /
857 strings, and a C#12 probe with all analyzers enabled. An adapter extracts
2,880 diagnostic/code-fix vectors from the unmodified upstream test sources.
It preserves literal/InlineData inputs, static helper settings, indentation,
XML include contents, hidden rule diagnostics and exact fixed text. All 89
exported providers must execute passing actions across those vectors and 16
owned probes, including file rename/split, added settings files, UTF-8 encoding,
reference-aware renames, semantic tuple fixes and an actual Fix All callback.
An additional internal shared ordering provider is exercised by upstream tests.

This is not the original xUnit suite. Unsupported helper control flow,
non-inline data, combined synthetic analyzers and other custom test framework
behavior are listed explicitly in the fixture corpus's `skipped` entries.
Compiler diagnostic assertions are excluded from the adapter's expected counts:
this port uses Roslyn 4.9.2 rather than the older compiler test baseline, whose
parser recovery diagnostics differ. StyleCop diagnostics remain exact, including
hidden diagnostics. Original input line endings are preserved during analysis;
only CR characters in final output comparisons are normalized. The full
upstream behavioral suite and full PowerShell integration remain broader work.
Some upstream analyzer classes deliberately implement no diagnostic; their
empty message formats and disabled behavior are preserved.

NuGet packages include all 427 production source inputs, original resx/XML
inputs, licenses, provenance and generated-source/check data. Generator binaries,
compiler libraries, private signing keys and PDBs are not bundled. Every file
entry is explicit to avoid recursive wildcard omission in NuGet packing.

Run `makepkg --cleanbuild --force --noconfirm` in CLANG64. Source is a pinned Git
checkout and `prepare.py` verifies its full tree against the original signed
commit before building. If using an already verified local VCS source cache,
`--holdver` prevents an unnecessary network update; it does not bypass source
verification. Build checks regenerate the fixture corpus and compare the exact
baseline before packing. After installing both split packages, run:

```bash
bash check.sh NEW_OUTPUT
```

The output directory must be new. It restores only from the installed feed with
an empty cache, checks source identities/inventories/resources/generation,
executes every extracted vector and owned structural probe, compares independent
PE metadata, and verifies real MSBuild analyzer selection via only the requested
meta-package. A bad comma must fail with SA1001 and its correction must build.
The SDK compiler remains untouched; consumers choose installed csc49 explicitly.

For port development, the focused source entrypoints are also available:

```bash
python3 verify-source.py SOURCE
python3 prepare.py SOURCE NEW_PREPARED
bash build-libraries.sh NEW_PREPARED
bash check-prototype.sh NEW_PREPARED NEW_CHECK SOURCE
```

The .NET 8 retarget supplies the nullable/compiler support types which upstream
obtained through `Nullable` and `TunnelVisionLabs.LanguageTypes.SourceGenerator`
for older frameworks. They are not runtime implementation dependencies here.
The original rules use the source-built Roslyn libraries; the normal SDK
compiler is left unchanged. Nine nullable warnings remain in upstream code
under newer annotations. MIT and third-party notices, including Apache-2.0
attribution, are retained by both packages. `Apache-2.0.txt` supplies the full
standard Apache License text for the Code Cracker portions listed upstream.
