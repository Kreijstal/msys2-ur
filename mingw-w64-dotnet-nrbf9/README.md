# Source Formats.Nrbf 9.0.11 NET9 profile

Builds the original NET9 reader from runtime commit
fa7cdded37981a97cec9a3e233c4a6af58a91c57. All46 selected production C# inputs
are unchanged. Original implicit source discovery,CLSCompliant(false),Open key,
experimental SYSLIB5005 annotation and16 neutral resource values are retained.
Compiler-generated XML documentation is included and its producer/package/cache
bytes are verified,as required by the original intellisense packaging policy.
The desktop targeting-pack membership preserves assembly version9.0.0.0.

The upstream repository requests SDK9.0.111 and preview language mode. This
bootstrap uses the source Roslyn5.3 compiler with CSharp13 semantics:its newer
preview Span conversion/overload rules select ReadOnlySpan overloads in unchanged
source that requires Span. The language adapter is explicit in the shipped
policy and build records. Exact upstream preview-toolchain reproduction is not
claimed and remains part of the unfinished toolchain work.

Source NET9 reference contracts drive compilation. Source SDK8 supplies build
tasks,evaluation and source-only NuGet restore. A fresh restore selects exact
9.0.11 and the original NET9 compile/runtime asset;package/cache/consumed DLL
bytes must match. The original81 public/protected CLR API entries and nullable
annotations are compared against the checked-in NET9 reference source.

A source NET8.0.31 formatter serializes14 owned fixtures;no deserialization is
performed by that producer. The source NET9 reader runs on source NET10.0.5 and
checks Unicode,primitive and numeric values,jagged/rectangular/heterogeneous
arrays,classes,shared/cyclic references,record maps,typed accessors and stream
ownership. Six malformed inputs are rejected. The described fixture assembly
must never load and object deserialization callbacks must never execute.
The experimental diagnostic is suppressed only in the test fixture,matching the
original Resources.Extensions consumer policy;it remains on the library.

The original source contains only neutral Strings.resx and no localized resource
inputs. All16 values are compared at runtime. Original source/project/resource
and language/version policy bytes are audited against the pinned archive.

The restore fixture disables implicit framework references and accepts NET9
explicitly;compilation separately uses all164 source NET9 refs. This supplies
neither SDK9 nor a NET9 runtime. Other original NET8/NETStandard/NETFramework
profiles,exact upstream preview compiler support,remaining9.0.11 libraries,
full MSBuild/SDK10,PowerShell7.6 and all other compatibility gates remain open.
