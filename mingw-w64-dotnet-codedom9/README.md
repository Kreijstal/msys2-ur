# Source CodeDom 9.0.11 NET9 profile

Builds the original NET9 CodeDom implementation selected by its pinned runtime
source project, commit fa7cdded37981a97cec9a3e233c4a6af58a91c57. Original production
C# sources are unchanged. The original CLSCompliant(true) policy and unsupported
platform attributes are preserved. Source NET9 reference contracts and source CSharp5.3
compile it; execution checks use the source NET10.0.5 runtime. The original
Arcade version calculation is inherited from the pinned source reference-pack
build policy document, rather than claiming an official Microsoft build number.

All955 original public/protected CLR API shapes must match the checked-in NET9
reference source, including accessibility, static/virtual/abstract status, bases,
interfaces, parameter types/defaults, properties and constants. Three nullable
annotation differences remain visible: the nullable-oblivious reference source
and the shared implementation source annotate CodeTypeReference's string
constructors and ArrayElementType differently. Original runtime null behavior is
checked. Strict nullable metadata equality is not claimed.

The source archive contains one neutral resource file with22 strings and no
localized resource inputs. All22 values are verified at runtime. Fresh consumers
restore exact9.0.11 only from the candidate or installed source feed, select the
NET9 compile/runtime asset, compare package/cache/DLL bytes and exercise Unicode
CSharp/VB generation. Both generated language outputs compile using source-built
compilers and execute. The original external-compilation API's
PlatformNotSupportedException behavior is preserved.

Source SDK8 is used only for source build tasks, evaluation and NuGet restore.
The restore fixture disables implicit framework references and explicitly sets
its maximum accepted TFM toNET9; compilation separately uses all164 source NET9
reference assemblies. This does not supply SDK9 or a NET9 runtime.

Other original NET8/NETStandard/NETFramework profiles remain unfinished, as do
the remaining9.0.11 libraries,full MSBuild/SDK10,PowerShell7.6 and the complete
PowerShell dependency and compatibility goal.

The original XML documentation is selected from the pinned binary-free
Microsoft.Private.Intellisense9.0.0-preview-20241010.1 transport data,net/1033.
Producer,package and fresh restored-cache XML bytes are compared.
