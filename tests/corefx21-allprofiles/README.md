# Original Immutable1.5 / Metadata1.6 profiles

Source commit: `30ab651fcb4354552bd4891619a0bdd81e0ebdbf`.

Five distinct original implementations build with C#7.3 and warnings as errors:
Immutable netstandard1.0, netstandard1.3 and netstandard2.0; Metadata
netstandard1.1 and netstandard2.0. All 8,483 original public API entries,
assembly attributes, dependency identities, resource strings and native version
data match their immutable published metadata baselines. Raw production C# is
unchanged. Both original portable DLL aliases are byte aliases of the matching
older Standard implementations.

Three isolated fixture pairs execute every candidate implementation on the
installed source NET8 runtime. Checks cover every immutable collection family,
structural persistence, profile-specific reference APIs, concurrent publication,
PE metadata writing/reading, portable PDB round trips and malformed inputs.
The fixtures verify exact original assembly identities and candidate load paths.
Historical runtime execution is not claimed.

The older Metadata compiler references are now packaged and installed; see
[the four-reference package report](../metadata16-contracts/package-results-20261031.json).
The library archives preserve all seven original DLL and XML paths, encoded
portable directory names, original dependency groups, licenses, version and
designer context files. XML is disclosed nonexecutable documentation data from
the original packages: CoreFX used Microsoft.Private.Intellisense
2.0.0-preview3-26209-0, whose official NuGet URL currently returns 404.
Compiler-generated XML differs from that external documentation. Its provenance
and unchanged hashes are recorded under inputs.

Fresh NS2 PackageReference consumers restore the exact candidate archives and
execute their exact DLLs in isolation. A strict fresh NS1.3 restore remains
incomplete: NETStandard.Library1.6.1 and numerous original System.* framework
packages are missing from the source feed (NU1101/NU1603). No placeholders or
runtime package substitutes are supplied. Reference assemblies do not close
this runtime dependency graph.

This workflow supplies the all-profile pacman package upgrade. The full
PowerShell dependency goal and original BuildTools/upstream matrix remain
incomplete. The historical prototype measurements are in
[the prototype report](prototype-results-20261031.json); formal package and
installed-check measurements are recorded separately in package-results files.

Installed validation (native Windows Python, with a source Csc4.4 directory):

    python.exe -X utf8 verify.py SOURCE_FEED NEW_OUTPUT CLANG64_PREFIX SOURCE_CSC44_DIRECTORY
