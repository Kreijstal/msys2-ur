Experimental SDK-pinned TemplateEngine NET10 source bootstrap.

The seven original libraries compile and run with unchanged VMR sources.
The stronger API baseline remains failed with two original IMacroDependency
entries; the source declares IMacroConfigDependency. Packaging preserves the
strict failure and its exact report. Other original framework profiles and
complete SDK integration remain open.

[Profiles, dependency flow and verification scope](../tests/templateengine10/README.package.md).
`makepkg --cleanbuild --force --noconfirm` passed. Final archive audit,
installation and fresh installed-feed checks passed: seven NuGet archives,
483 original compile items,70 resource sets/2268 values,65 satellites and seven
PDBs. Owned-folder and NuGet template installation/generation/uninstall pass.
The stronger all-seven API gate still exits1 with the two unchanged original
entries; its complete failure report is packaged. Pacman reports242 files and
zero alterations. All254 pre-existing source archives remain unchanged.

[Exact commands, hashes and gate results](../tests/templateengine10/package-results-20261031.txt).
