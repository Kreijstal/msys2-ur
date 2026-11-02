Original NuGet 6.13.2 NET10 source-only closure for TemplateEngine, from commit
5d81cb8da82eda8a6b47aae92d1e6f888de982ce.

Package 6.13.2-3 rebuilds all seven libraries against exact source dependencies:
Immutable 8.0.0, ASN.1 8.0.1, ProtectedData 4.4.0, Pkcs 6.0.4 and Newtonsoft.Json
13.0.3. Original package requirements remain unchanged. Producer and installed
consumer restores use warnings-as-errors and pass with zero diagnostics.

The clean build, final archive audit and fresh installed checks passed:
5,975 upstream API declarations, 502 resource values, seven PDBs, exact compiled
bindings and dependency execution in isolated contexts. Pacman reports 123
files with zero alterations; all 23 coexisting NuGet archives retain their
hashes. Candidate restore uses one feed view with exact candidate precedence
and mandatory archive/cache byte equality.

[Exact commands and results](../tests/nuget6132/package3-results-20261031.txt).
The earlier same-version source race and its fix remain recorded in
[package 2 results](../tests/nuget6132/package2-results-20261031.txt).

TemplateEngine's original strict central-version restore also passes from the
installed feed with no diagnostics. Full TemplateEngine rebuild, analyzer
integration, the separate all-seven-project API baseline discrepancy, original
additional framework profiles and the overall PowerShell dependency goal
remain incomplete. See [validation scope](../tests/nuget6132/README.md).
