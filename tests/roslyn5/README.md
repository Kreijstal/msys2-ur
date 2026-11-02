# Original Roslyn5 dependency pins

The original NET10 compiler-task bootstrap is now packaged and installed as
`dotnet-roslyn53-msbuild-tasks-bootstrap 5.3.0.2.26113.113-1`. MSBuild18's
default Roslyn task registration and original CSharp/VisualBasic CoreCompile
targets pass NET10 execution,Unicode/PDB/editorconfig/error checks,all434 task
resource values and automatic shared-server lifecycle checks. The package has
13 original task satellites and39 byte-verified source compiler satellites.
Pacman reports168 entries /0 altered files;all94 compiler assets match the
installed source compiler packages. See
[`package commands,focused recovery and installed evidence`](net10-msbuild-tasks-package-results-20261029.txt).
The private MSBuild17 dependency package closure,additional original task
frameworks/metadata profiles and full SDK10/PowerShell7.6 remain open.

The original SDK10 NET10 MSBuild task now compiles all60 original C# inputs
against source MSBuild17.11.48 APIs and executes on source MSBuild18. CSharp14
and VB LINQ NET10 programs, Unicode source paths/output, portable PDBs and
CS0103/BC30451 propagation pass. Both tasks automatically start and share one
source NET10 compiler server; no command-line fallback, exact server process
image and owned-server shutdown pass. All31 neutral strings, original target,
identity and MSBuild references pass. Archive audits verify1195 MSBuild17.11
Compile items,37 source-only Collections inputs and60 Roslyn task Compile items.
See [`exact commands, failures and limits`](net10-msbuild-tasks-results-20261029.txt).
The MSBuild17.11 dependency closure uses explicit source SDK8 bootstrap DLLs;
formal dependency packages, original additional task frameworks/localization,
SDK-style builds and full SDK10/PowerShell7.6 remain open. Package counts are unchanged.

Original Common/CSharp5.0.0 libraries for Standard2.0 now build cleanly, are
installed and pass the full original API/compiler/resource checks, including
CSharp14 extension-property execution. Exact commands, retained warnings and
228 verified evidence files are in
[`package50-results-20261029.txt`](package50-results-20261029.txt).

The SDK's exact 5.3.0-2.26113.113 Common/CSharp Standard2.0 libraries are also
source-built and installed. All 10,560 original API declarations, 28 resource
sets with 39,508 strings, compiler execution, analyzers and generators pass.
The clean build, archive audit and fresh installed consumer each exited zero;
see [`package53-results-20261029.txt`](package53-results-20261029.txt).
This completes the two library packages' Standard2.0 profile.

The original VMR NET10 Common/CSharp/csc projects also compile, and the new
CLI runs on the installed source NET10 host. CSharp14, Unicode response files,
Regex generation and invalid-source diagnostics pass. The independent source
audit verifies 2,210 pinned original source/project inputs. See
[`net10-cli-results-20261029.txt`](net10-cli-results-20261029.txt).
The NET10 CSharp compiler bootstrap package is now installed, including all 26
localized satellites. Its fresh build, source/tool/archive audits, full API and
resource suite, installed checks, SDK8 MSBuild task integration and corrected
shell launcher pass. The launcher fix was narrowly repackaged with every
compiler/satellite byte unchanged; see
[`csharp53-package-results-20261029.txt`](csharp53-package-results-20261029.txt).

All six original NET10 primary compiler projects now compile, including the VB
compiler, vbc and compiler server. The three VB generators produce all five
original generated VB files and grammar exactly. The new vbc compiles and runs
a NET10 program using LINQ and async/await; invalid source returns the expected
error. See [`net10-toolset-results-20261029.txt`](net10-toolset-results-20261029.txt).
The VB/client/server companion is now installed too. It preserves all 6,096 VB
APIs, 25,228 localized strings, 13 satellites, original friend identities and
embedded templates. The installed suite executes VB programs and verifies real
CSharp/VB server requests without fallback, with owned-process shutdown. Both
CMD and MSYS clients also auto-start and share the correct NET10 server when
they inherit an SDK8 host setting. See
[`visualbasic53-package-results-20261029.txt`](visualbasic53-package-results-20261029.txt).

The CSharp launcher host-selection fix is installed as release3; all compiler
and satellite bytes remain unchanged from its clean build. Its latest evidence
is [`csharp53-package3-results-20261029.txt`](csharp53-package3-results-20261029.txt).
Together the packages provide all six primary NET10 compiler projects and all
39 satellites. Original SDK10 MSBuild/compiler tasks and other framework/tool
profiles remain unfinished.

The pinned SDK10 manifest requires MSBuild18.3.0-release-26113-113 from commit
228caa11ad0046ccb599530abd9aba4e1979b5e9. The source archive is downloaded and
hashed; it has not been built. The exact pin and profile boundaries are in
[`sdk10-msbuild-source-pin-20261029.json`](sdk10-msbuild-source-pin-20261029.json).

PowerShell7.6 requires Microsoft.CodeAnalysis.CSharp5.0.0. Its publisher metadata
pins Roslyn commit6c4a46a31302167b425d5e0a31ea83c9a9aa1d09.
SDK10.0.201 instead declares compiler5.3.0-2.26113.113 from VMR commit
05d9490471fb4b10d7ef4faa32c423e1b5adcaee, whose original manifest maps Roslyn to
2333221c0564852ee5ceac9c622a0b14e864d76e.

[`source-pins-20261029.json`](source-pins-20261029.json) records both downloaded
source archive hashes, original dependency/project hashes, published Common5.0
profile dependencies and source-build maintenance overrides. The VMR mapping
comes from the [pinned original source manifest](https://raw.githubusercontent.com/dotnet/dotnet/05d9490471fb4b10d7ef4faa32c423e1b5adcaee/src/source-manifest.json).

Memory4.6.3, Unsafe6.1.2 and Tasks.Extensions4.6.3 are now separately source-built
and installed; see [their validation](../maintenance10/package-results-20261029.txt).
The installed Compiler5 host remains an inherited source bootstrap profile.
Original CLI/other framework profiles for Roslyn5.0, the SDK's full Roslyn5.3 graph
and all required host profiles are not complete. PowerShell's generator also declares Immutable9.0.14; the
existing9.0.0 package does not establish that version's completion.
