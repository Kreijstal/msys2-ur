# Cecil 0.11 source prerequisite

Builds all four original netstandard2.0 libraries (Cecil, Rocks, Mdb and Pdb)
from tag0.11, commit12da1bf7e0e10278e05eeb23adfc72760bbb6668. Original C#,
NET_CORE/CECIL/INSIDE_ROCKS guards, public identity, private signing key and
the Pdb project's0649 suppression remain unchanged. Compilation additionally
requires warnings-as-errors. Every selected compiler input is checked against
the original explicit project items. Binary fixtures from the archive are
excluded and inventoried.

The source SDK8.0.131/NET8 bootstrap builds an isolated original Roslyn4.4 csc
driver (11 unchanged inputs) against installed source Roslyn4.4 NS2 libraries.
That build-only driver retains the original interface BeforeFieldInit metadata.
The initial compiler5 probe failed the strict metadata comparison; it is kept
as evidence and is not the compiler selected for the package. An early driver
probe used the wrong source checkout and was discarded. The final driver reads
and verifies the pinned4.4 source archive directly. It does not change any
installed compiler selection or post-process the Cecil assemblies.

Fresh source-only consumers verify all3,844 public metadata entries against a
frozen inventory from published NS2 DLLs, without loading those DLLs as code or
using them as compiler references. Original and rewritten owned IL execute1 and42;
Rocks macro transforms, nullable metadata transfer, resource insertion and
portable/embedded PDB round trips pass. MDB/native-PDB providers are loaded but
complete native-format fixtures and upstream test-suite coverage remain open.

The package contains only the original NS2 profile. The upstream net40 profile
remains unbuilt; it is not advertised in the NuGet archive. Version0.11.0.0 from
the original nuspec is normalized to NuGet0.11.0. Original deprecated licenseUrl
metadata produces a NU5125 pack warning. Complete original root/CCI licenses and
the symbol writer's original source copyright/license headers are retained.
The full PowerShell dependency port remains open.

Installed validation:

    /usr/bin/python3 /clang64/share/doc/dotnet-cecil011-bootstrap/check.py /clang64/share/doc/dotnet-cecil011-bootstrap NEW_OUTPUT /clang64/lib/dotnet/library-packs
