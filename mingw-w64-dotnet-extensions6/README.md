Microsoft.Extensions 6.0 source libraries for NuGet and PSResourceGet
==================================================================

These three packages retain the complete original Core implementation of
Microsoft.Extensions.Primitives, Microsoft.Extensions.FileProviders.Abstractions
and Microsoft.Extensions.FileSystemGlobbing 6.0.0 from dotnet/runtime commit
4822e3c3aa77eb82b2fb33c9321f923cf11ddde6. They target the source .NET8 runtime,
preserving original source assembly/file/informational identities and the
adb9793829ddae60 signing identity. Original C# algorithms are unchanged.

The original project declarations retain their shared HashHelpers and
EmptyDisposable inputs. The original common System.SR implementation handles
resource formatting; generated glue supplies only resource properties and the
ResourceManager binding. Both original English resource manifests are retained
for each assembly, with all20 string entries. The source .NET8 runtime provides
the actual Unsafe implementation used by Primitives.
Redundant explicit System.* references use the same SDK targeting-pack inputs.
The checksum-verified archive is extracted into a short root with every file in
the three original src directories and their declared shared inputs. This avoids
Windows resource path limits without altering source or resource contents.

The packages supply lib/net8.0 implementation and reference metadata assemblies,
XML documentation, licenses and exact source inventories. Published NuGet DLLs
are used only for metadata baselines, never executed or included as build inputs.
These libraries are prerequisites for the complete NuGet6.9.1/PSResourceGet1.1.1
graph; they do not complete that graph or update the source CLR's servicing level.
