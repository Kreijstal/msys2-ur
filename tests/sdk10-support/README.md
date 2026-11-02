# Exact SDK10 runtime support packages

The clean package build, independent archive audit and installed consumer pass.
Pacman reports63 entries and0 altered files. See
[exact commands and results](package-results-20261029.txt) and
[archive audit](package-audit-20261029.json).

`mingw-w64-dotnet-sdk10-support-bootstrap` supplies the original NET10 profiles
for System.IO.Hashing10.0.2, Microsoft.Extensions.DependencyModel10.0.2 and
Microsoft.NET.HostModel10.0.2-servicing.25612.105 required by SDK10.0.201.
The source VMR is44525024595742ebe09023abe709df51de65009b; its runtime baseline
is9ffface2f3fa6fbbb427793c3230b1626a1fdd84. All133 compiler inputs are unchanged.

The actual VMR contains version-policy edits beyond its mapped upstream commit.
The source archive says patch1; the VMR says patch2. Source acquisition verifies
2636 support/shared source files against VMR git blob identities, retains those
edits and freezes the exact source view. The original Arcade resource/version
task sources execute in an explicit standalone source SDK8 helper host.
OfficialBuildId20251212.105 reproduces the original suffix/file-version rule.
HostModel also preserves the installer AssemblyVersion reset. See
[VMR source/version evidence](vmr-source-policy-20261029.json).

Strict metadata comparison preserves257 original Hashing/DependencyModel contract
entries with zero missing,extra,changed or nullable differences. HostModel has no
separate reference-source project here. Runtime checks exercise19 upstream hash
vectors,streaming/reset,large payloads,software-intrinsic fallback,10 original
resource values,deps JSON Unicode/metadata/runtime-graph roundtrip and actual
Unicode Windows apphost/bundle creation/execution. The native template is the
installed source8.0.31 apphost and the generated application uses source10.0.5.
No XLF translations are supplied by these original resource directories.

`prepare.py`, `build.py`, `check-api.py` and `check.py` retain the initial prototype
work. The recipe freezes the tested standalone package and installed-check
workflow. An initial reference-check fixture incorrectly included a non-NETCore
source item; it was corrected to honor the original ItemGroup condition. The
initial bundle fixture passed Hello.dll where the API expects the simple name
Hello; only that fixture changed. Production source remained unchanged.

Additional original frameworks,full upstream tests,full original Arcade/analyzer
integration and broader HostModel formats/COM/resource behavior remain open.
Deployment.DotNet.Releases,its compatible original JSON NS2 profile/version flow,
SDK build/APICompat/Extensions tasks and full SDK10/desktop10/PowerShell7.6 remain
required,along with earlier broad compatibility gates. The full goal is incomplete.
