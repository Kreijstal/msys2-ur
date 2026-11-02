# Source Compiler5 bootstrap host

This package hosts the installed source-built desktop Compiler5 on the source
.NET8 runtime. It retains the bootstrap compiler's DLL and command-line bytes,
builds a small managed argument adapter, and builds original Immutable9 and
Metadata9 implementations for their supported net8.0 target. Explicit host
dependency metadata makes those implementations available to newer analyzers.

The compiler comes from the declared dotnet-bootstrap-tools package. This is a
host for that bootstrap profile; it does not claim a new complete upstream
Roslyn5 package build. The two runtime9 libraries are built from commit
9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3, archive SHA256
32755d528ead386762fb9da054249f6151ac78ef6a92f437044838cd0ab00def.

The package uses an empty NuGet feed and the declared source SDK/compiler
dependencies. It does not depend on the private PowerShell/.NET10 build roots.
The original compiler and existing SDK compiler selection are unchanged.

Validation covers a real SDK build using C#14 extension properties, source
generation and analyzer callbacks, exact runtime9 dependencies inside the
generator process, emitted execution, Unicode/space response files, and invalid
source exit status. Source audits compare every original compilation input
against the pinned archive and every inherited compiler file against its owner.

Installed entry point:
`lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/csc50.cmd`.
Select its directory with CscToolPath and csc50.cmd with CscToolExe when needed.
The wrapper resolves the dotnet host relative to its installed location.

The larger PowerShell dependency goal, complete .NET10 SDK/framework integration
and formal packaging of the remaining generator dependencies remain open.
