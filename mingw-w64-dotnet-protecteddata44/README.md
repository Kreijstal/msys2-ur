Original CoreFX ProtectedData4.4.0 NETStandard2 reference, Windows and portable source bootstrap.

See [source, backport and validation scope](../tests/protecteddata44/README.md).
The old2017 toolchain, original NETFramework and older harvested profiles remain open.

`makepkg --cleanbuild --force --noconfirm` passed. The final archive audit,
installation and fresh installed-consumer checks passed: 32 payload hashes,
21 strict API entries across the reference/Windows/portable DLLs, native DPAPI
interoperability including empty input, both neutral resource sets and both PDBs.
Pacman reports53 files and zero alterations. Existing ProtectedData8/9 archives
remain unchanged.

[Exact commands, hashes and results](../tests/protecteddata44/package-results-20261030.txt).
TemplateEngine's unchanged strict restore now selects exactly4.4.0. Its remaining
two diagnostics concern Pkcs6.0.4 and the fallbackPkcs8 exactASN.1 constraint.
The full dependency goal is incomplete.
