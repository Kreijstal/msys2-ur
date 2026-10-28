# Serviced .NET8 targeting pack for the source SDK

This candidate builds all163 .NET8.0.31 reference assemblies and all eight
original interop/COM/Regex/JS/JSON generator projects from pinned source. The
generators target the source .NET8/Roslyn4.9.2 host. Their original netstandard2.0
and historical Roslyn host compatibility remains unfinished; this is an explicit
host port, with no production C# source reductions. Browser/WASM execution also
remains unverified. It does not complete the full PowerShell dependency objective.

The pack includes all99 signed generator/resource DLLs, their byte-verified
source-built dependency closure, full supporting license files and the complete
original-template platform manifest. Private/native manifest entries describe
package conflict resolution, including other platforms and optional components;
they do not claim those native payloads were built. Optional API XML documentation
from the upstream private Intellisense package is not included.

The existing source targeting package owns the same8.0.31 pack directory. This
package conflicts with that owner and provides its source SDK8.0.131-2 component
role, so pacman can replace ownership without an overwrite flag. It installs one
serviced8.0.31 pack, superseding the bootstrap's reference aliases. Source SDK
compiler selection requires the declared Roslyn4.9 compiler and SDK analyzer
provider. The source SDK, runtime packs and complete shipping PowerShell remain
separate requirements.

Run `makepkg --cleanbuild --force --noconfirm` in MSYS2 CLANG64; it downloads
the workflow and bootstrap archives from the msys2-ur release. The workflow
scripts are in [workflows/runtime-servicing](https://github.com/Kreijstal/dotnet-mingw-bootstrap/tree/master/workflows/runtime-servicing);
`python3 make-source.py <dotnet-mingw-bootstrap checkout>` packs them, but the
published archive predates the current `check-installed.sh`, so the result
differs in that one file. The build audits
original compiler inputs/resources and the complete managed source dependency
closure. Checks run SDK copies with normal pack selection and no analyzer or
compiler override, plus all JSON generator variants and JS import compilation.
Formal package/artifact/installed ownership checks must pass before relying on
this candidate. This README does not claim those unfinished gates passed.

Candidate1's clean build was stopped after a framework-forwarding regression
identified bad stub keys and missing zero-reference versions. Candidate2 reads
the original stub signing keys, runs the unchanged upstream GenFacades version
postprocessor and audits all20 stub identities/all22 reference shims. Its normal
clean build requires the corrected runtime8.0.31-3 package. No stopped candidate1
artifact was installed.
