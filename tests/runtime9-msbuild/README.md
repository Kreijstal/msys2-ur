# Exact runtime 9.0.11 MSBuild prerequisites

The NET9 9.0.11 reference pack is source-built, packaged and installed as
`mingw-w64-dotnet-reference9-servicing 9.0.11-1`. Its 164 public contracts pass
fresh installed metadata and NET9-positive/NET8-negative compiler checks. All
175 payload files match the package and source outputs; pacman reports zero
altered files. See [`../reference9/package-results-20261029.txt`](../reference9/package-results-20261029.txt).

CodeDom9 is a source prototype using its original NET9 target. All120 selected
original C# files, the original project and neutral resource bytes match the
pinned runtime archive. Its 22 neutral resource strings, signing/target identity,
Unicode CSharp/VB generation, identifier escaping and original unsupported
compiler API behavior pass. Both generated language outputs compile with the
source compilers and execute to42. Execution uses the source NET10.0.5 runtime;
this does not supply or prove a NET9 runtime. See
[`codedom-prototype-results-20261029.txt`](codedom-prototype-results-20261029.txt).

The NET9 CodeDom profile is now source-built, packaged and installed as
`mingw-w64-dotnet-codedom9 9.0.11-1`. All955 CLR API entries match the original
NET9 reference source. Three original nullable annotation differences are
recorded; strict nullable metadata equality is false. The source archive has
one neutral resource file and no localized resource inputs; all22 values pass.
All9 package payloads match installation and pacman reports zero altered files.
See [`codedom-package-results-20261029.txt`](codedom-package-results-20261029.txt).

The NET9 MetadataLoadContext profile is also packaged and installed as
`mingw-w64-dotnet-metadataloadcontext9 9.0.11-1`, with original servicing assembly
version9.0.0.11. All16 public/protected API entries and nullable annotations match,
and all53 resource values pass. AnyCPU/x86 metadata, Unicode, generics, custom
attributes, resolver/cache identity, stream loads, disposal and execution
rejection pass. An additional check inspects real source NET10 CoreLib,Roslyn
and csc metadata without runtime loading. See
[`metadataloadcontext-package-results-20261029.txt`](metadataloadcontext-package-results-20261029.txt).

The NET9 Formats.Nrbf prerequisite is packaged and installed as
`mingw-w64-dotnet-nrbf9 9.0.11-2`,including compiler-generated XML documentation.
All81 public/protected CLR API entries and nullable annotations match. All16
resource values,14 independently generated source NET8 payloads and6 malformed
input checks pass,including shared/cyclic references,jagged/rectangular arrays,
stream ownership and no described-type loading. The original SYSLIB5005
experimental annotation is retained. The source Roslyn5.3 bootstrap uses CSharp13
semantics because its newer preview Span overload rules reject unchanged source;
exact upstream SDK9 preview-toolchain reproduction remains unverified. See
[`nrbf-package-results-20261029.txt`](nrbf-package-results-20261029.txt).

The original NET9 Resources.Extensions profile is now packaged and installed as
`mingw-w64-dotnet-resources-extensions9 9.0.11-1`. All20 APIs/nullable annotations,
52 resource values,primitive/BCL interoperability,typed converters,stream
activation,NRBF class/self-cycle reconstruction and callbacks pass. Exact source
NRBF dependency and pinned original IntelliSense XML bytes are verified. The
original exact MemoryStream fast path still ignores closeAfterWrite;the general
stream path honors it,and both are tested. See
[`resources-extensions-package-results-20261029.txt`](resources-extensions-package-results-20261029.txt).

Original IntelliSense9.0.0-preview-20241010.1 XML is now included in CodeDom9
and MetadataLoadContext9 release2. All5 prior NuGet entry contents are byte-for-byte
unchanged in each package;only the original XML entry was added. Paired installation,
all payload bytes and fresh installed consumers pass. See
[`documentation-pair-results-20261029.txt`](documentation-pair-results-20261029.txt).

Other original framework profiles remain unfinished.
Cryptography.Pkcs and Cryptography.Xml9.0.11 remain. Full MSBuild/SDK10,WindowsDesktop,PowerShell7.6,original
framework/tool variants and all remaining compatibility gates remain active.

ProtectedData9 original NET9 profile is packaged and installed as `9.0.11-1`.
All7 CLR API entries and nullable annotations, both neutral resources, original
XML, 24 DPAPI roundtrips, 4 independent Windows C crosschecks and40 GC lifecycle
cases pass. Both exact-source interop generators rebuild privately on NET8 with
source Workspaces4.9.2; their original NETStandard2.0/toolset profiles remain open.
Pacman reports21 entries and zero altered files; all12 regular payloads match.
See [`protecteddata-package-results-20261029.txt`](protecteddata-package-results-20261029.txt).

EventLog9 Windows NET9 prototype now compiles all66 original C# inputs. All419
CLR API entries/nullable metadata and41 resource values match. Classic/modern
read-only queries, metadata, bookmarks, independent native query, callbacks and
GC/disposal checks pass on source NET10. The source-regenerated Win32 message
resource is byte-identical to upstream and all65536 IDs pass native formatting.
The unsupported-platform assembly, formal package/install and other original
framework/toolset profiles remain open. See
[`eventlog-prototype-results-20261029.txt`](eventlog-prototype-results-20261029.txt).

EventLog9 is now packaged and installed as `9.0.11-1`, including both original
NET9 profiles and the original NETStandard2.0 message DLL. Both main assemblies
match419 APIs/nullable metadata. Fresh Windows NuGet selection, live classic/modern
operations, generic PNSE behavior, all65536 native messages and all3 DLL identities
pass. All14 installed regular payloads match;pacman reports23 entries and zero
altered files. Exact generator toolsets and other EventLog frameworks remain open.
See [`eventlog-package-results-20261029.txt`](eventlog-package-results-20261029.txt).

ConfigurationManager9 original NET9 profile is packaged and installed as `9.0.11-1`.
All251 original C# inputs and261 archive inputs match. All210 neutral resources,
XML,exact source dependency archives,configuration/typed-settings/DPAPI persistence
and12 concurrent loads pass. All1220 external API entries are compatible;99 raw
reference/implementation metadata differences remain recorded and strict raw
equality is false. The original RSA provider PNSE is retained. All11 installed
payloads match;pacman reports20 entries and zero altered files. See
[`configuration-package-results-20261029.txt`](configuration-package-results-20261029.txt).

PKCS9 and Cryptography.Xml9 now have original NET9 source prototypes. PKCS builds
Windows241/generic153 CS;XML builds80 CS. All59 ASN models regenerate through
original targets/XSLT,and private source ASN.1 builds41 CS and matches215 APIs.
PKCS matches384 reference entries with1 inherited override extra;XML matches440
with5 public serialization-exception extras explicitly covered by upstream CP0001.
Raw metadata equality remains false. All77/94 resources,crypto/GC cases and
bidirectional OpenSSL checks pass;PKCS also executes exact source ASN.1. Formal
package builds,documentation and installed-feed checks remain unfinished. See
[`crypto-prototype-results-20261029.txt`](crypto-prototype-results-20261029.txt).

PKCS9 and Cryptography.Xml9 are now standalone source-built packages installed
as `9.0.11-1`,including original Intellisense XML. Both clean makepkg builds and
fresh installed-feed consumers pass. PKCS rebuilds exact-source interop tools,
private ASN.1 and59 ASN models;all77 PKCS/34 private ASN.1 strings pass. XML
checks all94 strings and exact source PKCS Windows asset selection. Original
raw extras remain documented:1 PKCS inherited override and5 XML serialization
exception entries covered by upstream policy. All15/12 installed payloads match
the packages;pacman reports zero altered files. See
[`pkcs-package-results-20261029.txt`](pkcs-package-results-20261029.txt) and
[`cryptography-xml-package-results-20261029.txt`](cryptography-xml-package-results-20261029.txt).

All6 exact NET9 OOB library packages for MSBuild18 are present with documentation
in the installed source feed. The feed inventory is
[`msbuild18-net9-feed-gate-20261029.json`](msbuild18-net9-feed-gate-20261029.json).
Full MSBuild/SDK10,desktop10,PowerShell7.6,other original framework/tool profiles
and the remaining original compatibility gates remain active.
