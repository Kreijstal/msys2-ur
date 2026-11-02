# Source-built .NET8.0.31 servicing framework

This candidate adds the complete168-assembly8.0.31 shared framework and its
versioned hostfxr beside the source bootstrap's8.0.0 runtime. It uses the existing
dotnet muxer. It ships no replacement targeting pack, SDK, Mono runtime or vendor
implementation. The full dependency objective, SDK/native compatibility work and
PowerShell7.6/.NET10 support remain open.

The recipe builds the native host/CoreCLR/JIT/compression, matching CoreLib,
original interop/Regex generators, complete reference set and all framework
libraries from pinned source. It retains17 native-port patches with one zero-fuzz
rebase, independently audits source/compiler/output inventories and runs actual
runtime and original source PowerShell checks. Existing MinGW limitations include
disabled DAC/out-of-process debugging and the GNU exception/SEH shim.

The isolated source build and execution checks pass. Formal clean package build,
artifact audit and fresh installed-package/SDK checks remain required. This README
does not claim those unfinished gates passed.

Build in MSYS2 CLANG64 with the declared source tools installed:

```bash
makepkg --cleanbuild --force --noconfirm
```

makepkg downloads the workflow and bootstrap archives from the msys2-ur release.
`python3 make-source.py <dotnet-mingw-bootstrap checkout>` recreates the workflow
archive byte for byte from [workflows/runtime-servicing](https://github.com/Kreijstal/dotnet-mingw-bootstrap/tree/master/workflows/runtime-servicing).

The sources and outputs stay under the new build root. The recipe does not replace
installed SDK files while building or testing. The package owns only its versioned
shared-framework/hostfxr paths and its license/provenance documentation. Installing
it makes normal patch roll-forward select8.0.31; retaining8.0.0 permits explicit
older-version execution. Consumers must still be validated before this is treated
as the completed servicing prerequisite.

Candidate2 also rebuilds the original Arcade file-version task pinned by the
runtime sources. Its reproducible source-date build number20260820.0 produces
file8.0.3126.42000 while the runtime product remains8.0.31. This preserves the
upstream ordering used by host dependency resolution. A regression requires a
fresh source NuGet JSON8.0.5 consumer to load the serviced framework bytes even
when the older private DLL is present. The prior simplified file version failed
that test; its package build was stopped and no artifact installed.

Candidate2 subsequently completed the clean package/artifact/install gates and
local runtime/PowerShell/CIM/WMI/JSON checks. An additional reflection regression
then found a framework-forwarding defect: compile-only stubs ignored their
project signing key, and the bootstrap helpers omitted the original
GenFacadesForceZeroVersionSeeds policy. System.Data therefore requested SqlClient
with an incompatible key/version. Installed2 remains a known affected candidate.

Candidate3 reads each original stub signing key and runs the unchanged pinned
Arcade ClearAssemblyReferenceVersions task on the original22 framework shims.
The focused private runtime SqlClient regression passes. Clean builds now audit
all20 used stub identities and all22 reference/runtime shim policies and run six
source-NuGet forwarding regressions. Fresh candidate3 clean/artifact/install gates
remain required; this does not claim full native or PowerShell completion.
