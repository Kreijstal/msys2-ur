# Source-built Microsoft.CodeAnalysis.Analyzers 3.3.4

The complete Core/CSharp/VisualBasic payload builds from commit
`22ea6422f85b05ca0793cc3b76375487be407f5d`, archive SHA256
`49a992347546aef48cb31673b294bd1b10c30e68bbb53be61d411bb0d7219e1e`.
All 152/11/11 original inputs are retained. The original source hashes and two
explicit compile substitutions are recorded: qualify the existing
Analyzer.Utilities.DocumentBasedFixAllProvider against a newer Roslyn name
collision; remove an invalid colon from the activated record-pattern branch.
No analyzer or code-fix implementation is removed. Original version-dependent
feature flags are enabled for the source-built Roslyn 4.9.2 dependencies.

Assembly/file identity 3.3.8.6701/31bf3856ad364e35 matches published metadata;
NuGet version is 3.3.4. Informational version retains 3.3.4 plus the source commit.
Only the production public key is used; the repository's private test key is not
used. Assemblies are public-signed from that public key. Published implementation DLLs are inspected only as metadata/resource
bytes, never executed, compiled against for production or used as generator input.

All 325 public/protected declarations, 23 analyzer classes, 13 exported code-fix
providers, 46 diagnostic ID constants, 145 neutral strings and the 1122-byte
banned-symbol resource match independent published metadata. CRLF representation
is derived from original text. All thirteen XLF satellites are built; every
string in all 14 resource sets/2030 strings is checked. All analyzers execute
callbacks without exceptions across 34 declared language combinations.

All 68 selected upstream and 10 owned cases pass. Actual passing actions cover
every one of the 13 exported fixers, including descriptor literal correction,
release-tracking document creation and entry edits, generated Fix All overrides,
and real C#/VB PreferIsKind Fix All diagnostic-provider callbacks. Used/unused
nested-record probes exercise the corrected record-pattern branch. Every one of
the sixteen consumer implementation/satellite DLLs matches the final source build.

The adapter checks diagnostic counts, ordinary markup spans and exact resulting
source. Configured cases support explicit counts, source lists and action index;
code-action equivalence-key, iteration and original compiler-diagnostic assertions
are outside the adapter. Unsupported configured/helper/member-data/additional
cases are explicitly recorded. This is not the full original xUnit suite or proof
of all provider behavior. Newer annotations produce upstream nullable warnings.

All fifteen original config/documentation generator sources build against source
Roslyn libraries and run offline with the source-built analyzer payload. All 554
outputs match independent published text after line-ending comparison: 500 global
configs, 25 rulesets, 25 editorconfigs, two MSBuild files and two generated docs.

The package retains all thirty original analyzer asset paths (sixteen unique
implementation/satellite DLLs), all 554 regenerated configuration/docs files,
original install/uninstall script sources, analyzer configuration documentation,
complete MIT license and third-party notices. The scripts retain original text;
published signature blocks are not reproduced. Original production/generator
sources, two compiled source overlays, resource/XLF sources and build provenance
are attached. The NuGet package has no implementation dependency downloads and
bundles no compiler or workspace binaries, private keys, PDBs or vendor signatures.

Actual CSharp and VB MSBuild checks select the two correct language-specific
analyzer assemblies from NuGet. Missing EnableConcurrentExecution must fail with
RS1026; its correction builds through the installed source csc49/vbc49 hosts.
Fresh installed checks restore from only the installed source feed with empty
caches. Full PowerShell integration and runtime servicing remain separate work;
the installed runtime reports8.0.0 despite SDK package label8.0.131.

On CLANG64 with source-built SDK, Common/CSharp/VisualBasic and both Workspaces
4.9.2 libraries installed, choose new output directories:

```bash
python3 prepare.py PINNED_SOURCE NEW_PREPARED
bash build-libraries.sh NEW_PREPARED
bash generate-config.sh NEW_PREPARED PINNED_SOURCE
$MINGW_PREFIX/lib/dotnet/dotnet.exe NEW_PREPARED/fixture-tool/bin/Release/net8.0/Tool.dll PINNED_SOURCE/src/Microsoft.CodeAnalysis.Analyzers/UnitTests > fixtures.json
bash check-prototype.sh NEW_PREPARED NEW_CONSUMER fixtures.json
```

Build and check the package with `makepkg --cleanbuild --force --noconfirm`.
After installation, choose a new output directory and run `bash check.sh NEW_OUTPUT`.
The default data directory is the installed share/doc/dotnet-codeanalysis-analyzers.
These gates are focused integration checks and do not replace the complete
upstream framework/xUnit, provider or IDE suites.
