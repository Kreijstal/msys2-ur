# Original NET10 Roslyn5.3 MSBuild task bootstrap

This package builds all60 original NET10 task C# inputs from SDK10-pinned Roslyn
commit2333221c0564852ee5ceac9c622a0b14e864d76e. Exact MSBuild17.11.48 source
APIs are privately rebuilt for compilation. Their OOB closure uses explicit
source SDK8 DLL bootstrap inputs;formal exact MSBuild17 dependency packages,
original additional frameworks and version policy remain open.

The runtime layout extends source MSBuild18 with its original Roslyn folder:
the task DLL,13 original XLF satellites,unchanged compiler target files,and an
original-target-generated CompilerApiVersion file. The bincore subtree contains
byte-verified source compiler/server assets and all39 compiler satellites from
the installed source CSharp/VisualBasic5.3 packages. No source SDK8 files are
replaced. MSBuild's original default task registration discovers this layout.

Checks use original CSharp/VisualBasic CoreCompile targets,execute NET10 CSharp14
and VB LINQ outputs,check Unicode/PDB/error behavior,verify all original task
resources,and prove that the installed tasks auto-start/share one source NET10
compiler server with no local fallback and owned-server shutdown.

This is a source bootstrap package. Original NET472/bridge profiles,full SDK10
restore/build,WindowsDesktop10,PowerShell7.6 and existing compatibility gates
remain open. `checks/check-installed.py PREFIX NEW_OUTPUT` repeats focused
validation with native CLANG64 Python. Package/source/reference/compiler-asset
hash evidence is under this documentation directory.
