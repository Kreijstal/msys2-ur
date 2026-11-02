# Original Registry 4.3 and CodePages 4.0.1 Windows source builds

Registry uses CoreFX commit `4d1af962ca0fede10beb01d197367c2f90e92c97`;
CodePages uses `9688ddbb62c04189cac4c4a06e31e93377dccd41`. Both compile their
original Windows netstandard1.3 sources with no production C# edits, original
assembly/file versions and public signing identity. Informational versions disclose
the source SDK8/runtime8/Csc4.4 bootstrap. Public signing is not Microsoft's private
signature. The original buildtools host is not replayed.

The build requires the source legacy contract pack revision 3: its Debug contract
retains the original Conditional("DEBUG") metadata. Revision 2 produced an extra
Debug dependency in the Registry Release build; the strict dependency check rejected
it. No dependency baseline or compiler warning was suppressed to fix that failure.

Checks require all 106 original public API entries and both original runtime
dependency identity sets. All 184 source resource strings and exact codepages.nlp
bytes are checked. A consumer compiled against source Standard1.x contracts runs
the exact old DLLs in an isolated load context on source runtime8. It tests native
Registry OS queries, both views, typed values, owned HKCU key CRUD, borrowed handles,
read-only/disposed errors and cleanup. Encoding tests cover exact CP1252/Shift-JIS
bytes, multiple legacy encodings, streaming surrogate state, strict fallbacks,
concurrency and the Windows active code page.

The NuGet port preserves the original Standard1.3 dependency groups. It adds
Standard2.0 compatibility assets that are byte-identical to the original Standard1.3
source build and explicitly depend on source NETStandard.Library2.0.3. Fresh Standard2
PackageReference consumers must restore with zero diagnostics and run the same
metadata/resource/native checks. The packaging host targets NET8 only to create
the archives; it does not recompile or retarget either production library.

CodePages' NET46 asset is also byte-identical to its Windows Standard1.3 asset in
the published package; that shared layout is preserved. Registry's NET46 facade,
Unix profiles, the original Standard1.3 runtime NuGet closure, old runtime execution
matrix and full upstream suite remain open. The full PowerShell dependency goal
remains open.

Installed NuGet check:

Revision 2 also compiles the original reference sources: Registry's compiler
contract is assembly 4.0.0.0 while its implementation is 4.0.1.0. CodePages retains
its original opaque reference contract. All 102 reference API entries and dependency
identities are checked separately from the 106 runtime entries. NuGet consumers
must select the reference assets for compilation and execute implementation bytes.

    /usr/bin/python3 /clang64/share/doc/dotnet-legacy-windows-support-bootstrap/check-nuget.py /clang64/share/doc/dotnet-legacy-windows-support-bootstrap NEW_OUTPUT /clang64/lib/dotnet/library-packs
