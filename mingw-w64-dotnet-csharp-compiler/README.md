# Source CSharp command-line compiler 4.9.2

Builds the upstream csc Program, complete CscCommandLine Compile list and complete
ExternalAccess.RazorCompiler helper from Roslyn commit
9934fb9e3527e1c0c51314e57d4aab30f97e8f9e. Compiler library dependencies are the
separately packaged, source-built Microsoft.CodeAnalysis.Common/CSharp 4.9.2.
Their DLLs and all satellite cultures accompany the tool and are audited against
the installed NuGet packages. SDK/vendor implementation DLLs are not payloads.
The source archive's binary fixtures are discarded before building.

PowerShell's 4.9 analyzer/source-generator graph needs this host: the installed
8.0.131 SDK csc is 4.8 and rejects 4.9-referencing analyzers with CS9057. This tool
installs under lib/dotnet/compiler-packs/roslyn-4.9.2 and reports 4.9.2 (9934fb9e).
It does not change the SDK compiler or global compiler selection.

Select it explicitly in SDK builds (using the native Windows path):

    -p:CscToolPath=E:/msys64/clang64/lib/dotnet/compiler-packs/roslyn-4.9.2 -p:CscToolExe=csc49.cmd -p:UseSharedCompilation=false

csc49.cmd locates dotnet.exe relative to its own installation and forwards all
arguments and the compiler exit code. Direct csc.dll tool selection uses an
unsuitable host in the current SDK task; this wrapper chooses dotnet explicitly.
The compiler also runs directly as dotnet csc.dll. XML documentation analyzers
need GenerateDocumentationFile=true, as PowerShell's source project requests.

Build in CLANG64: makepkg --cleanbuild --force --noconfirm
After installing, run with a new output/cache directory:

    bash mingw-w64-dotnet-csharp-compiler/check.sh NEW_OUTPUT

Checks copy the tool into a temporary compiler-packs path containing spaces and
Unicode, run actual MSBuild analyzer and incremental-generator callbacks against
Roslyn 4.9, require the generated compiler identity and value, reject an owned
negative fixture, compile CSharp 12 through a Unicode response file, verify error
exit status, and require the original SDK compiler hash to remain unchanged.
All restore sources are the installed source-built feed. Temporary tool copies
are removed after checks. Original friend identities, source lists, signing keys
and license provenance are retained; public signing is not a private Microsoft
signature.

This package is the .NET 8 command-line CSharp host, not the full upstream
Microsoft.Net.Compilers.Toolset NuGet distribution. The separate VBCSCompiler
server, Visual Basic compiler, MSBuild/IDE tooling and full PowerShell build
remain separate work. Checks use shared compilation off. Required core-runtime
servicing remains open; this package does not upgrade the current 8.0.0 runtime.
