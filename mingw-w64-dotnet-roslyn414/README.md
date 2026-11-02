# Source Roslyn4.14 compiler library prerequisites

Builds Microsoft.CodeAnalysis.Common and Microsoft.CodeAnalysis.CSharp4.14.0
for their original Standard2.0 target from commit
`8edf7bcd4f1594c3d68a6a567469f41dbd33dd1b`.
The three original C# compiler-generation tools build from source and regenerate
all five compiler outputs. Every output must match its original baseline after
the upstream console tool's documented line-ending/BOM/blank-line cleanup.

Original projects are evaluated in Release with the original source-build
version policy and central package definitions. All selected production C#
inputs remain unchanged. All resources/translations and friend declarations
are retained. Signing keys are checked against the original Settings.props.
Actual source maintenance and runtime9 versions satisfy the original minima;
CodePages7.0.0 resolves to the declared source9.0.0 implementation.

Compiler and reference inputs come from installed source packages. The workflow
does not require a private CoreCLR/cDAC, Roslyn or generated-output directory.
The current SDK compiler selection is unchanged; this package installs two
versioned NuGets in the source feed with documentation and license/notices.

Fresh Standard2.0 and NET8 consumers check source package/DLL bytes, C#13 parsing
and semantics, deterministic PE/portable-PDB emit and execution, diagnostics,
cancellation, analyzers, incremental generators and the complete original
public API/resource baselines. Audits verify original archive inputs, actual
producer/consumer compile/cache bytes and all generated/compiler/license assets.

Run `python make-source.py`, then in Windows CLANG64 run
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
Installed checks use `check.py ARCHIVE_ROOT PREPARED NEW_CONSUMER
/clang64/lib/dotnet/library-packs` followed by
`audit.py ARCHIVE_ROOT PREPARED NEW_CONSUMER`.

Original NET8/NET9 compiler variants, VB, Workspaces, Roslyn4.4 and the complete
runtime10 shipping-generator bundle remain required parts of the full goal,
alongside complete framework/SDK/desktop10, PowerShell7.6 integration and the
other open compatibility requirements.
