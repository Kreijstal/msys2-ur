# Microsoft.NETCore.Platforms1.1.0 source runtime graph

Exports the original data-only package from corefx v1.1.0, commit
8808e3e7f9749a168f86180496d6ea0f8e159db2. The original pkgproj declares1.1.0.
The graph's117 runtime identifiers and import ordering match the release data;
the published JSON uses CRLF and the Git source uses LF. Packaging keeps the
original Git bytes. There are no implementation assemblies.

The separate1.1.2 package remains installed unchanged. This exact1.1.0 archive
satisfies NETStandard.Library2.0.3's original minimum without the NU1603 fallback
reported by warnings-as-errors restores. It does not replace the SDK's current
runtime graph or change targeting references.

Validation uses a fresh source-only cache, warnings as errors, exact archive and
graph bytes, the source SDK's NuGet RuntimeModel, every RID's complete import
closure/cycle/expansion and representative Windows/Linux/macOS fallback chains.
The original legacy corefx build-tool chain has not been replayed; this is a
source data-packaging port. The full PowerShell dependency goal remains open.
