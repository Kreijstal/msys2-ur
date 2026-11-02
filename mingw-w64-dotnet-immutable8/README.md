Exact System.Collections.Immutable 8.0.0 original NET8 source bootstrap. See
[validation scope](../tests/immutable8/README.md) for source provenance and
remaining original framework profiles.

The clean build (`makepkg --cleanbuild --force --noconfirm`), final archive audit,
installation and fresh installed consumer checks passed on win11. Strict API
comparison checked 782 entries with zero CLR or nullable differences. All 16
resource values and the portable PDB association passed; pacman reports 50 files
and zero alterations. The existing Immutable9 archive and shared NET8 runtime
DLL retain their original hashes.

[Exact commands, package hash and results](../tests/immutable8/package-results-20261029.txt).
TemplateEngine's unchanged strict restore now selects exactly8.0.0, removing
its Immutable NU1603 error. Pkcs6.0.4, ProtectedData4.4.0 and the current fallback
Pkcs8/ASN.1 constraint remain open. The full dependency goal is incomplete.
