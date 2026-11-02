# Source NET10 VisualBasic and compiler-server bootstrap

Builds the SDK10.0.201-pinned Roslyn5.3.0-2.26113.113 NET10 VisualBasic compiler,
vbc client and VBCSCompiler server from original sources. It complements the
installed source NET10 Common/CSharp/csc package. Together they provide all six
original source-only VMR NET10 compiler projects under one compiler directory.

All three VB generators build from their original sources on the source NET8
host. Five generated VB files and grammar must match original baselines. The
source VBC4.9.2 compiler bootstraps the NET10 VB library; the installed new NET10
CSharp compiler builds the clients, server, satellites and validation programs.
These explicit bootstrap tool-host profiles remain distinct from a complete
source SDK10 build.

Checks cover all 6096 original VB API declarations, 14 resource sets with 25228
strings, 13 satellites, original friend identities and four embedded templates.
Real compilation exercises queries, XML literals, iterators, anonymous types,
generics, async/await, analyzers, source generation, portable PDBs, checked and
unchecked arithmetic, embedded VB runtime, cancellation and localized errors.
The compiler-server check uses a private pipe, four real CSharp/VB requests,
executed outputs, negative diagnostics, absence of local fallback and explicit
shutdown of its owned process. Actual sources and input/output bytes are audited.

Use vbc53-bootstrap from MSYS or select vbc53.cmd with MSBuild VbcToolPath and
VbcToolExe. The launcher preserves slash options and converts existing MSYS
source/response paths; paths within options and response files use Windows
compiler paths. Compiler-server and VB assemblies share the existing CSharp
compiler directory without replacing any CSharp-package files.
Both entry points set DOTNET_HOST_PATH for their process so automatic server
startup uses NET10 when the default SDK is still NET8.

Original net472 and other framework/tool profiles, SDK10 MSBuild tasks, a full
SDK10 and WindowsDesktop10, PowerShell7.6 and all remaining dependency and
compatibility gates are unfinished. Full runtime compatibility remains subject
to the runtime bootstrap's recorded limits.
