# Source NET10 CSharp compiler bootstrap

Builds the SDK10.0.201-pinned Roslyn5.3.0-2.26113.113 Common, CSharp and csc
NET10 projects from commit2333221c0564852ee5ceac9c622a0b14e864d76e.
The original VMR source-only framework properties select NET10. All six
compiler CLI projects are evaluated; this package supplies the three CSharp
projects, with their original source inputs, signing identity, resources and
all26 localized satellites. VB, vbc and the compiler server remain dependencies
to build separately for the full SDK toolset.

The installed source Compiler5/SDK8 host bootstraps code generation, project
evaluation and primary compilation. The new NET10 compiler builds its own
satellites and consumer checks on the source NET10 host. The source NET10
reference pack supplies all167 framework contracts. Runtime implementation
DLLs are not substituted into the compiler API model.

Checks cover all10560 original public API declarations,28 resource sets with
39508 strings,13 cultures, German diagnostics, CSharp14 execution, Unicode
response files, analyzer loading, incremental generation, portable PDBs,
cancellation and invalid-source error status. Actual source/archive and
reference/output bytes are audited. Original source nullable warnings remain
visible. Full runtime compatibility is limited by the runtime bootstrap.

The package installs under lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap.
The shell command is csc53-bootstrap; MSBuild can select csc53.cmd through
CscToolPath/CscToolExe. Default compiler selection is unchanged.
The shell launcher preserves slash options and converts existing source and
response-file paths from MSYS. Paths inside compiler options and response
files use native Windows paths, as accepted by the Windows compiler.
Both launchers set DOTNET_HOST_PATH for their process so automatic compiler
server startup uses the source NET10 host even when SDK8 is the default.

Build with python make-source.py --update-checksum, then Windows CLANG64
makepkg --cleanbuild --force --noconfirm. Full SDK10, all compiler profiles,
WindowsDesktop10, PowerShell7.6 and the remaining dependency/compatibility gates
remain unfinished.
