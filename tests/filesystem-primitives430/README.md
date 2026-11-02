# Original System.IO.FileSystem.Primitives 4.3.0 source package

Builds the original Standard 1.3 reference (assembly 4.0.1), the real Standard 1.3
enum implementation (assembly 4.0.2), and the complete four-forwarder Framework
4.6 facade (assembly 4.0.2). The original runtime implementation depends on
System.Runtime 4.0.20; the reference profile depends on 4.0.0. These scopes and
versions remain distinct. The Framework ref/lib facade aliases are byte-identical.

Pinned source-build-reference-packages commit
5aeee2738338530a92d7f6caa2c7d5f569fed3c4 supplies the reference declarations.
Pinned CoreFX commit 4d1af962ca0fede10beb01d197367c2f90e92c97 supplies the four
unchanged implementation enum files and original facade/project declarations.
The reference compilation projection keeps the original declarations and supplies
an explicit original assembly header. No extracted source is edited in place.

The original NuGet is a frozen metadata and data baseline. No publisher DLL is
executed, used as a compiler reference or shipped. Source Csc4.4 compiles against
exact source legacy contracts, with warnings as errors. Native version resources
and original assembly headers preserve the published metadata. Original XML,
license, notice and marker data are copied with SHA256 checks.

The checker compares every original API entry, identity, attribute, dependency,
native version, resource and full exported-type record. It compiles and executes
typed consumers, independently loads the actual source enum implementation,
checks every enum constant and flag parsing, and resolves all four facade targets
to source NET8 implementations. Original Framework runtime execution remains
unverified. Fresh own-package restores and the real NETStandard.Library1.6.1
restore report their actual dependency results. Full PowerShell compatibility and
historical runtime/provider closure remain separate required work.
