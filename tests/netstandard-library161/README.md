# Original NETStandard.Library 1.6.1 dependency metadata

This metapackage contains dependency metadata and original license text.
Its original package contains no DLLs, executables or empty framework markers.
It does not provide implementations or a targeting pack.

The source project at CoreFX 4d1af962ca0fede10beb01d197367c2f90e92c97 declares
PackageVersion1.6.1 and the same 43 framework package names. The original
published dependency groups are frozen as declarative metadata: NS1.0, NS1.1,
NS1.2 and NS1.3 contain 23, 30, 31 and 44 versioned dependencies respectively.
Microsoft.NETCore.Platforms remains1.1.0; all other minima remain4.3.0.
Original Microsoft .NET Library license text and notices are retained with
unchanged hashes. Source-project MIT licensing and original package licensing
are recorded separately.

Validation uses source SDK8 NuGet APIs to check every dependency version range
and six nearest-framework selections. Fresh restore probes for all four
frameworks verify exact1.6.1 selection and archive cache bytes. Missing source
framework packages are recorded as remaining work; no dependency is removed or
replaced to make a restore pass. The full dependency and historical runtime
goals remain incomplete.

Native Windows Python check:

    python.exe -X utf8 check.py SOURCE_FEED NEW_OUTPUT CLANG64_PREFIX
