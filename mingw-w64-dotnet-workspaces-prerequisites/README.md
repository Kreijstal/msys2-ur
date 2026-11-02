# MEF2 and Pipelines prerequisites for Roslyn Workspaces

This split recipe builds six libraries and the `System.Composition` dependency
package, all NuGet version **8.0.0**, from the pinned runtime **v8.0.31** source.
It supplies dependencies needed to build Roslyn Workspaces, which in turn is
needed for the remaining PowerShell analyzers and their code fixes.

| NuGet ID | Assembly identity |
| --- | --- |
| System.Composition.AttributedModel | 8.0.0.0 / b03f5f7f11d50a3a |
| System.Composition.Runtime | 8.0.0.0 / b03f5f7f11d50a3a |
| System.Composition.Hosting | 8.0.0.0 / b03f5f7f11d50a3a |
| System.Composition.Convention | 8.0.0.0 / b03f5f7f11d50a3a |
| System.Composition.TypedParts | 8.0.0.0 / b03f5f7f11d50a3a |
| System.IO.Pipelines | 8.0.0.0 / cc7b13ffcd2ddd51 |
| System.Composition | Dependency package; no implementation assembly |

These are net8.0 assets for the source-built .NET 8 distribution. The MEF2
assemblies are distinct from `System.ComponentModel.Composition` (MEF1).
Project source lists and .NET 8 conditional compilation are retained; the
upstream project-reference graph must match `libraries.json`. Resources are
compiled from source, and binary inputs in the extracted source are discarded.
Libraries are public-signed with the original public identities; no Microsoft
private-key signatures are claimed. File version 8.0.31.0 and informational
version `8.0.0+runtime-v8.0.31` identify the actual servicing source.
The meta-package depends on all five MEF2 packages and contains a net8.0 asset
placeholder without a dummy implementation DLL.

The metadata-only baseline records **317** published public/protected API
entries, including enum values, parameter names/defaults and signatures.
`published-metadata-provenance.json` records exact package URLs, hashes and
selected assets. Published binaries are only read as metadata; they are never
executed, compiled against, used as build outputs or shipped. The gate rejects
any missing or extra API entry or changed assembly identity.

The consumer gate verifies source identities, local implementation selection,
all exported types, CLS compliance and all 70 strings in five resource sets.
MEF2 checks cover constructor/property/named imports, shared parts, lazy metadata,
import completion, instance exports, conventions, sharing boundaries, disposal
and missing/ambiguous contract errors. Pipelines checks cover asynchronous
backpressure/resume, UTF8 buffer contents, reader advancement, completion,
pending-read cancellation, stream bridges and ownership, and producer errors.
Framework implementation modules are rejected.

Build in MSYS2 CLANG64:

    makepkg --cleanbuild --force --noconfirm

After installing all seven packages, use a new output directory/cache and only
the installed source-built feed:

    bash mingw-w64-dotnet-workspaces-prerequisites/check.sh NEW_CONSUMER /clang64/share/doc/dotnet-composition2/localization.json
    bash mingw-w64-dotnet-workspaces-prerequisites/check-api.sh NEW_CONSUMER NEW_API

These checks establish this dependency layer. Roslyn Workspaces, the analyzers,
full PowerShell integration, broader composition/threading/race coverage and
required core-runtime servicing remain separate unfinished work. This recipe
does not upgrade the currently source-built 8.0.0 core runtime.
