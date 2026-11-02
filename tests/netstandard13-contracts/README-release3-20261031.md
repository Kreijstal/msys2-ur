# Selected legacy Standard 1.x source reference contracts

Latest package: `dotnet-legacy-ns13-contracts-bootstrap 20261031-3` passed a full
`makepkg --cleanbuild --force --noconfirm` and fresh installed checks. Revision 3
uses original CoreFX Debug source to restore 23 Conditional("DEBUG") method
attributes omitted by SBRP. All 47 public Conditional attributes across the
contracts match published metadata; a Release consumer omits Debug.Fail in IL.
The unchanged Registry source exposed this gap by retaining an extra Debug
dependency, which the strict library check rejected. Pacman reports 108 files and
0 altered. [Current package evidence](package-results-20261031.txt).

The earlier revision 2 was packaged and installed as `dotnet-legacy-ns13-contracts-bootstrap 20261031-2`.
The clean source build, source audit and metadata/consumer checks passed; packaging
then exposed the historical CoreFX license filenames. After that packaging-only
fix, `makepkg --repackage --force --noconfirm` exited 0. Revision 2 corrects the
installed Csc5 driver's filename lookup. All 38 reference DLL payloads are
unchanged between revisions. The fresh installed check with source Csc5 exited 0;
pacman reported 107 files and 0 altered. All 273 feed archives are unchanged.
The [package report](package-results-20261031.txt) retains exact commands and
failed/successful logs; [structured results](package-results-20261031.json) and
the [external archive audit](artifact-audit-20261031.json) record hashes and gates.

These references support the original Registry 4.3.0 and CodePages 4.0.1 source
builds. They come from Microsoft's source-build reference snapshot
`5aeee2738338530a92d7f6caa2c7d5f569fed3c4` and original CoreFX commit
`9688ddbb62c04189cac4c4a06e31e93377dccd41`. Sixteen root contracts require
22 original assembly-version variants, including System.Runtime 4.0.0 and 4.0.20.
The original Standard 1.0 through 1.3 source profiles and assembly identities are
retained. Twenty-one variants compile unchanged original C# sources. Interop has
one explicit source port that restores four missing attribute classes and three
COM struct declarations directly from the pinned original CoreFX file; no raw
extracted source is modified in place. COM layout and field offsets are checked.

The bootstrap uses source SDK/runtime 8 and an isolated source csc 4.4 driver.
Original reference-source warning suppressions and the SDK's standard 1701/1702
defaults are recorded; warnings as errors remains enabled. All outputs retain the
reference-only marker. They are compiler inputs, not runtime implementations.
The build does not create NuGet runtime archives or register a replacement SDK
targeting pack.

Checks compare all 7,430 public entries in the root contracts and all 11,600 entries
across the 22 variants, plus original signing identities, dependency reference
identities and reference-only markers. Published DLLs are read as metadata only.
A consumer compiles against only the source-built legacy contracts, then exercises
collections, Unicode streams, reflection, marshaling, cancellation, asynchronous
tasks and a negative control on the explicitly selected source NET8 runtime host.

The first strict dependency check rejected a build that used Runtime 4.0.20 for
every contract. The corrected build uses the original lower-profile dependency
variants. That failed check remains evidence; its baseline was not weakened.

The SBRP snapshot omits Diagnostics.Contracts and the SuppressMessageAttribute
part of Diagnostics.Tools. Those two references use complete original CoreFX
source files, with generated version attributes taken from the pinned SBRP header.
The failing original API check remains evidence; the baseline was not reduced.
The full Standard 1.x runtime NuGet closure,
historical runtime execution matrix and Registry/CodePages packages remain open.
The complete PowerShell dependency goal remains open.
