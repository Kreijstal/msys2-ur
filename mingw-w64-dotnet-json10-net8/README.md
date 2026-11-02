# Original JSON10 NET8 implementations

Builds original runtime10.0.5 System.Text.Json, System.Text.Encodings.Web and
System.IO.Pipelines projects for their declared NET8 target. The source SDK
evaluates every original project/shared source input. All original production
C# inputs remain unchanged. Original versioning.targets supplies CLS compliance,
alias, resource language, serviceable/inbox metadata and DLL-search policy.
Source keys and the Arcade version task are verified against pinned archives.
NuGets retain original package prose/licenses, XML documentation and peer
project dependencies. The JSON package includes the current original source-only
Roslyn4.4 JSON analyzer and its translations from the installed generator pack.
The installed source Regex10 generator and Compiler5 host compile JSON internals.

The fresh package consumer checks original public/protected API declarations,
metadata/resources, exact restored package and assembly bytes, real generated
JSON contracts, DOM/UTF8/streaming/schema/encoding and pipelines behavior.
The existing SDK/framework assemblies are not replaced.

Run `python make-source.py`, then Windows CLANG64:
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
Remaining original NET9/NET10/Standard/Framework/browser variants, source ILLink
library processing and trimming/AOT gates, final targeting-pack/SDK integration,
complete framework/desktop10, PowerShell7.6 and compatibility gates remain open.

The pinned source has one known reference/implementation nullability difference
on JsonStringEnumConverter<T>.CreateConverter. The API gate requires those two
exact original annotations, while checking all other declarations/shapes.
Original JSON NETCore reference inputs include the netcoreapp and type-forward
files in addition to the common API file; all are compared to the archive.
