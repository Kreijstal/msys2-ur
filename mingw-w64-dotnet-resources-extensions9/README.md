# Source Resources.Extensions 9.0.11 NET9 profile

Builds the original NET9 source at runtime commit
fa7cdded37981a97cec9a3e233c4a6af58a91c57,including its shared CoreLib reader,
writer and resource-set inputs. Production C# sources are unchanged.
The original desktop targeting-pack assembly9.0.0.0,Open key,CLS policy,
RESOURCES_EXTENSIONS define and SYSLIB5005 suppression are retained.
The exact source-built Formats.Nrbf9.0.11 asset supplies the original dependency.

All20 original public/protected CLR API entries and nullable annotations must
match the checked-in NET9 reference. All52 neutral resource values are checked.
The source production tree contains no localized resource inputs.
The original documentation policy selects System.Resources.Extensions.xml from
Microsoft.Private.Intellisense9.0.0-preview-20241010.1,net/1033. The exact pinned
transport package is audited to contain no implementation binaries;its XML
bytes are retained and compared through producer,NuGet and consumer cache.

Fresh source-only restore selects exact9.0.11 NET9 assets and exact source NRBF
bytes. Tests cover primitive/BCL resource interoperability,Unicode,typed strings,
string/byte converters,stream activators,files,duplicate names and invalid images.
Source NET8 generates owned NRBF payloads;on source NET10,the original resource
reader reconstructs strings,arrays and a user class/self-cycle through source
NRBF,including original callbacks and uninitialized allocation.

General streams honor closeAfterWrite. The unchanged original exact MemoryStream
fast path ignores closeAfterWrite;both branches are covered and the limitation
is retained explicitly. The plain BCL reader handles the ordinary format;
extended records intentionally select DeserializingResourceReader.

Source Roslyn5.3 uses CSharp13 semantics against all164 source NET9 references.
The source repository's SDK9.0.111/preview toolchain has not been reproduced;
this bootstrap language choice is recorded. Source SDK8 performs only evaluation,
build tasks and NET9 restore,with implicit framework references disabled and an
explicit maximum accepted TFM. Neither SDK9 nor a NET9 runtime is supplied.

Other original NET8/NETStandard/NETFramework profiles,binding-redirect outputs for
NETFramework,exact upstream preview tooling,remaining dependencies,full
MSBuild/SDK10,PowerShell7.6 and all remaining compatibility gates stay unfinished.
