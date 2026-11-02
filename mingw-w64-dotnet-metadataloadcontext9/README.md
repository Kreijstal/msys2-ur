# Source MetadataLoadContext 9.0.11 NET9 profile

Builds the original NET9 source profile from runtime commit
fa7cdded37981a97cec9a3e233c4a6af58a91c57. Original production C# files are
unchanged. Source NET9 references and source CSharp5.3 compile the library.
Source SDK8 supplies build tasks, evaluation and restore. Execution checks use
the source NET10.0.5 runtime; no NET9 runtime or complete SDK10 is supplied.

The original servicing rule makes this out-of-band assembly version9.0.0.11.
It is not in the runtime or desktop targeting-pack lists. Open signing identity,
CLSCompliant(true), original resource scope and the matching original Arcade
file-version calculation are preserved. The reproducible file version is
inherited from the source reference-pack policy document, without claiming an
official Microsoft build number.

The API gate compares all original public/protected CLR signatures and nullable
annotations against the checked-in NET9 reference source. A fresh source-only
NuGet restore must select exact9.0.11 and its NET9 compile/runtime asset; package,
cache and consumed DLL bytes must match. All neutral resource values are checked.
The pinned source contains no localized resource inputs for this library.

Source-built AnyCPU and x86 fixtures exercise Unicode constants, generics,
constraints, custom attributes, byref returns, optional/raw default values,
custom resolution, path/byte/stream loads, cache identity and independent
contexts. Tests reject method execution and attribute construction, invalid PE,
missing assemblies and metadata access after disposal. A module-initializer
sentinel and runtime assembly enumeration verify that inspected fixtures do not
execute or enter the runtime load context.

The NET9 restore fixture uses source SDK8's NuGet with implicit framework
references disabled and an explicit NET9 maximum TFM; compilation separately
uses all164 source NET9 reference DLLs. This does not supply SDK9.

Other original NET8/NETStandard/NETFramework profiles and their exact dependencies
remain unfinished, as do remaining9.0.11 libraries,full MSBuild/SDK10,
PowerShell7.6 and all other required dependency/compatibility gates.

The original XML documentation is selected from the pinned binary-free
Microsoft.Private.Intellisense9.0.0-preview-20241010.1 transport data,net/1033.
Producer,package and fresh restored-cache XML bytes are compared.
