# Original runtime9 source library components

Release3 keeps exact producer reference versions and packages maintenance
dependencies as minimum versions. Earlier package metadata used exact NuGet
constraints, which rejected Roslyn5's original source-build Memory4.6.3 and
Unsafe6.1.2 overrides. The packaging adapter changes only nuspec dependency
constraints and verifies every non-nuspec byte remains unchanged. Fresh consumers
exercise both the original and newer maintenance selections, treating NU1608 as
an error. All original source targets and existing framework variants are kept.

Builds eleven original .NET Standard2.0 library implementations and the original
System.Composition metapackage from runtime commit
`9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3`. All NuGets retain version9.0.0.
The five System.Composition libraries also contain independently compiled
original NET8 implementations. Microsoft.Bcl.AsyncInterfaces also contains its
genuine original Standard2.1 forwarding target and empty dependency group.
This component supplies the framework variants
needed by the Roslyn/runtime10 generator graph; other original target variants
are not claimed complete.

The implementations are Collections.Immutable, Reflection.Metadata, all five
Composition components, Bcl.AsyncInterfaces, IO.Pipelines, Threading.Channels
and Text.Encoding.CodePages. No production C# inputs are changed. Sources are
extracted from the pinned archive without executable binary inputs. Original
projects are evaluated in Release, including shared source conditions, public
keys, CLS overrides, DLL search policy, resources and original dependency minima.
Actual resolved maintenance versions are declared explicitly, without relabeling
implementations. File versions9.0.0.0 identify this source profile; informational
versions include the exact commit.

The original runtime9 interop generator projects build first on NET8 using the
declared installed source Roslyn4.9.2/Workspaces, satisfying their original4.8
minimum. They generate Metadata's original native ReadFile wrapper. The five
NET8 MEF implementations build independently and merge into their NuGets before
dependent package restores. All required compiler, references and maintenance
libraries come from installed source packages; no private build output is used.

Fresh consumers restore from source feeds into empty caches. The NET8 consumer
selects the genuine Standard2.1 forwarder and no downlevel Tasks dependency;
extern aliases verify shared framework type identity during compilation and
execution. Metadata checks retain all ten original forwarding declarations and
the nested exported type, Standard2.1 references and real runtime resolution.
Async enumeration, disposal and cancellation execute alongside NET8 MEF.
Isolated Standard2.0 execution
checks all eleven exact implementations, keys/revisions, original resources and
complete codepages data, immutable/frozen collections, real PE/metadata reading,
MEF imports/exports, async iterator disposal/cancellation, Unicode pipelines,
channels/backpressure/errors and strict/incremental code-page conversions. The
generated ReadFile wrapper runs with a real file handle.

The API gate uses the installed source Compiler5's actual compiler libraries as
a validation tool. It compares independent original reference-project sources
and independently built NET8 MEF metadata with the Standard implementations.
The shipping Roslyn4.14/4.4 dependencies remain separate required packages.
Audits compare original producer/API/resource/policy inputs with the archive,
actual cached packages/DLLs with source feeds, generated interop configuration,
and every shipped managed/resource/license asset with source build outputs.

Run `python make-source.py`, then in Windows CLANG64 run
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
After installing, run `check.py ARCHIVE_DIRECTORY PREPARED NEW_CONSUMER
/clang64/lib/dotnet/library-packs` and then
`audit.py ARCHIVE_DIRECTORY PREPARED NEW_CONSUMER NEW_NET8_CONSUMER` from the source workflow.
Run `check-net8.py PREPARED NEW_NET8_CONSUMER /clang64/lib/dotnet/library-packs`
to verify fresh NET8 asset selection and real composition execution as well.
The package installs twelve NuGets plus documentation and notices. It does not
replace framework implementation DLLs or the current SDK compiler selection.

Formal Roslyn and shipping-generator packages, remaining runtime9 target
variants, complete runtime/framework/SDK/desktop10 and PowerShell7.6 integration,
and the other open compatibility gates remain part of the active full goal.
The original AsyncInterfaces Standard2.1 forwarding target is included in
revision2. Other runtime9 framework variants remain part of the full goal.
