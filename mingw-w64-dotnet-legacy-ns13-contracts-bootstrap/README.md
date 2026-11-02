# Selected legacy Standard 1.x source reference contracts

These references support original Registry 4.3.0, CodePages 4.0.1 and Dataflow
4.6.0 source builds. They come from Microsoft's source-build reference snapshot
`5aeee2738338530a92d7f6caa2c7d5f569fed3c4` and original CoreFX commit
`9688ddbb62c04189cac4c4a06e31e93377dccd41`. The existing 16 highest root contracts and
33 exact assembly-version variants retain their original Standard 1.0 through
1.3 profiles. Lower Dataflow references deliberately use assembly 4.0.0.0;
substituting the highest available version would alter dependency metadata.
The ref/ directory retains its 16-file build interface for existing consumers;
all 33 variants, including the new lower references, are under contracts/.

Twenty-nine variants compile unchanged source. Four explicit generated source
ports restore declarations or attributes omitted by the reference snapshot:
Interop restores four attribute classes and three COM struct declarations from
the original CoreFX file; Debug's Standard 1.0 variant restores six original
Conditional("DEBUG") method attributes. Serialization restores the original
KnownTypeAttribute declaration; ObjectModel restores the original Synchronized
flags on eight abstract interface event accessors. No raw extracted file is
edited. The
Standard 1.3 Debug variant uses unchanged CoreFX source with all 23 conditional
methods. Diagnostics.Contracts and Diagnostics.Tools also use unchanged CoreFX
source to supply declarations missing from the snapshot.

The bootstrap uses source SDK/runtime 8 and a private source Csc 4.4 driver.
Compiler 5 bootstraps the original driver's 11 unchanged CLI inputs against
source Roslyn 4.4 libraries. Original reference-source warning suppressions and
SDK defaults 1701/1702 are recorded; warnings remain errors. All DLLs retain the
reference-only marker. They are compiler inputs, with no NuGet runtime archives
or replacement SDK targeting-pack registration.

Checks compare 7,430 root API entries and 14,637 entries across all 33 variants,
plus original signing/dependency identities, reference markers, COM layouts and
53 public Conditional attributes. Published DLLs supply metadata only. A source
consumer exercises the highest roots on source NET8. A separate consumer uses
only Dataflow's exact lower dependency graph and exercises concurrent
collections/LINQ, dynamic/object-model APIs, expressions, serialization
attributes and tasks. Both Release consumers must omit Debug calls from IL.

    makepkg --cleanbuild --force --noconfirm
    /usr/bin/python3 /clang64/share/doc/dotnet-legacy-ns13-contracts-bootstrap/check.py \
      /clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap NEW_OUTPUT \
      /clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap --installed

The installed consumer uses the source Csc5 host; package production uses Csc4.4.
The full historical runtime NuGet closure and original runtime execution matrix
remain open. Registry and CodePages have separate source packages with disclosed
NS2 compatibility assets; Dataflow and MSBuild Tasks remain separate work. The
full PowerShell dependency goal remains open.
