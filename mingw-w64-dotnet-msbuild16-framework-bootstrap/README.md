# MSBuild Framework16.0.461 source NS2 port

Builds the original netstandard2.0 profile from commit
6ff56ef63c3a1c9785d42fe2564d904ebd225ea0, with no production C# edits. The
original Framework project compile/remove items and source feature-policy target
select the full NS2 source set. Source SDK8/NET8 and an isolated original csc4.4
driver are bootstrap hosts. The original assembly15.1.0.0/public key and release
file/informational versions are preserved from the frozen metadata contract.
Public signing is not a proprietary Microsoft signature.

The port prunes two original NuGet references for this profile:
System.Runtime.Serialization.Primitives4.1.1 and System.Threading.Thread4.0.0.
The published Framework DLL references only netstandard2.0. The pruned build must
match that complete runtime-reference table and all743 public API entries.
Fresh source-only NS2/NET8 consumers restore with zero diagnostics and test task
contracts, Unicode message formatting, context identity/equality/negative controls
and DataContract serialization. Original source keys/guards/warning policy and
source reference-archive/DLL bytes are audited. Warnings-as-errors stays enabled.

The original net472 profile, original Arcade/Nerdbank/compiler toolchain, generated
GenAPI source replay and complete upstream runtime/tooling matrix remain open.
The original standalone DisableNerdbankVersioning option selects explicit version
metadata in the bootstrap. The legacy package versions pruned from this NS2 port
are not represented as separately completed packages. This package installs a
NuGet archive without replacing the installed SDK's Framework assembly.
The complete PowerShell dependency goal remains open.

Installed check:

    /usr/bin/python3 /clang64/share/doc/dotnet-msbuild16-framework-bootstrap/check-framework.py /clang64/share/doc/dotnet-msbuild16-framework-bootstrap NEW_OUTPUT /clang64/lib/dotnet/library-packs
