# SDK 10 MSBuild dependencies

The source NET10 Roslyn task bootstrap now installs the original Roslyn/bincore
layout into this MSBuild18 host. Its original CSharp/VisualBasic CoreCompile
targets pass with default task registration,including editorconfig generation,
NET10 program execution and shared-server operation. See
[`compiler-task package checks`](../roslyn5/net10-msbuild-tasks-package-results-20261029.txt).
Full SDK-style restore/build remains open.

SDK 10.0.201 declares MSBuild 18.3.0-release-26113-113. Its pinned source is
228caa11ad0046ccb599530abd9aba4e1979b5e9. Source and dependency pins are in
[`../roslyn5/sdk10-msbuild-source-pin-20261029.json`](../roslyn5/sdk10-msbuild-source-pin-20261029.json)
and [`dependency-source-pins-20261029.json`](dependency-source-pins-20261029.json).

The `mingw-w64-dotnet-msbuild18-bootstrap 18.3.0.26113.113-2` package is now
built and installed. All six projects and53 satellites came from a cold source
build. Release2 relocates the tool under `lib/dotnet10/build-packs` because
original MSBuild worker startup searches two parent directories for its host;
the initial SDK8-root layout failed the installed parallel check. All76 managed
DLL/PDB bytes are unchanged. The corrected installed shell/CMD launchers,default
tasks,Unicode,parallel workers and23597 localized values pass; worker traces
confirm NET10,and pacman reports156 entries /0 altered files. See
[`package commands,initial failure and installed evidence`](bootstrap-package-results-20261029.txt).

All six primary NET10 projects now compile from unchanged original source:
StringTools, Framework, Build, Utilities, Tasks and the MSBuild CLI. The pinned
original Arcade version task and MSBuild override produce file version
18.3.0.11413. CLI version/help, JSON properties, Unicode file tasks and a
parallel build with two distinct process IDs pass on the source NET10 runtime.
All 53 original XLF satellites compile; 118 resource sets / 23597 exact values
and German CLI help pass. Windows resource serialization preserves CRLF;
the checker accounts for that and inspects the English satellite directly
because the main assembly declares English as its neutral resource language.
See [`managed-build-results-20261029.txt`](managed-build-results-20261029.txt)
for commands, failure history, audits and remaining gates.

The managed prototype is packaged as an explicit bootstrap. Complete native
resource/content layout, SDK-style compilation, other original frameworks,
full SDK10/WindowsDesktop10/PowerShell7.6 and broader compatibility remain open.

The six original NET10 projects evaluate with 1326 Compile items, covering
1156 distinct original C# files. StringTools (8 original C# inputs) and
Microsoft.Build.Framework (179 original inputs plus 19 exact source-package
inputs) compile and execute in a focused consumer. Unicode span/builders,
20000 concurrent intern lookups, event contexts and task callbacks pass.
That initial foundation prototype used bootstrap file version 18.3.0.0.
See [`foundation-results-20261029.txt`](foundation-results-20261029.txt).

`mingw-w64-dotnet-solutionpersistence 1.0.52-1` is source-built and installed.
The original NET8 SourceBuild profile preserves all 217 upstream API declarations.
Fresh producer and installed-feed checks pass Unicode SLN/SLNX model roundtrips,
five original fixtures, invalid XML rejection and SLN cancellation. The original
synchronous XML reader ignores a pre-canceled token; this behavior is recorded.
All 93 selected original source/resource inputs match the pinned source archive.
See [`solutionpersistence-package-results-20261029.txt`](solutionpersistence-package-results-20261029.txt).

The directly required out-of-band runtime libraries must be built at
MSBuild's exact 9.0.11 versions: ConfigurationManager, MetadataLoadContext,
Resources.Extensions, CodeDom, Cryptography.Pkcs and Cryptography.Xml. The NET9
assets also require EventLog, ProtectedData and Formats.Nrbf 9.0.11. The pinned
runtime source archive is downloaded. All six direct NET9 libraries and their
EventLog, ProtectedData and Formats.Nrbf dependencies are now source-built,
packaged and installed, including original documentation XML. See the
[`exact installed-feed gate`](../runtime9-msbuild/msbuild18-net9-feed-gate-20261029.json).
Other original framework profiles, reference-only NETStandard project variants,
full MSBuild/SDK10, WindowsDesktop10, PowerShell7.6 and the existing compatibility
gates remain part of the full dependency goal.

The build helpers take native Windows paths when run with CLANG64 Python:

```sh
python prepare-version.py PLAN PINNED_ARCADE_ARCHIVE VERSION_OUTPUT
python build-all.py PLAN BUILD_OUTPUT - VERSION_OUTPUT/file-version.txt
python check-cli.py PLAN BUILD_OUTPUT CLI_OUTPUT
python check-parallel.py CLI_OUTPUT/stage PARALLEL_OUTPUT
python localize.py PLAN BUILD_OUTPUT CLI_OUTPUT/stage LOCALIZATION_OUTPUT
```

Each output must be new. The explicit `--resume-completed-satellites` option is
for checking the 53 already compiled satellites after a terminal checker-only
failure; it verifies staged primary DLL hashes and runs all resource assertions.
`audit-original-inputs.py EVIDENCE MSBUILD_ARCHIVE ARCADE_ARCHIVE SOURCE_PACKAGES
OUTPUT_JSON` independently compares the recorded inputs with the pinned archives.
