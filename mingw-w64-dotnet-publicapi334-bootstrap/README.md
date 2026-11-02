Original NS2 PublicApiAnalyzers 3.3.4 source port with source Roslyn4.4 bootstrap
references and the source .NET10 Csc5.3 host.

[Source selection, ports, original policies and validation scope](../tests/publicapi334/README.md).
Original Roslyn1.2 host compatibility and the full upstream toolchain/test suite
remain open. `makepkg --cleanbuild --force --noconfirm` passed. The final archive audit,
installation and fresh installed-feed checks passed: 47 strict CLR/nullable entries,
all five diagnostic cases, all three code-fix providers and their document fix-all,
812 resource values, both PDBs and 102 regenerated package policy/documentation
assets. The original Roslyn compile task consumes the NuGet imports and generated
warnings-as-errors globalconfig correctly. Pacman reports 70 files, zero altered;
all 253 existing source NuGet archives remain unchanged.

[Exact commands, hashes and results](../tests/publicapi334/package-results-20261031.txt).
