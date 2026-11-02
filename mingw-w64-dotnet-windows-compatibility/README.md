# Source Windows compatibility metapackage

This recipe produces Microsoft.Windows.Compatibility8.0.31 from the complete
pinned windowsdesktop metadata project. The upstream project has no library
outputs. All five original framework dependency groups and191 dependency entries
are evaluated by the source MSBuild and packed with source NuGet.Packaging6.9.1.
All groups match the published metadata-only baseline. Source package readme,
Arcade icon and original licenses are included without vendor implementation IL.

The metadata view removes the original NoTargets SDK import while preserving
every PackageReference and condition. The package has no compile outputs to
rebuild; its producer uses the already packaged source NuGet library. The
published nuspec is an independent comparison baseline, not a production input.
The original readme has LF line endings; published readme text is identical
after normalizing line endings. The icon matches the original source bytes.

Fresh Windows.NET8 checks restore only from the source-built feed and exercise
the complete35-edge graph. All restored archives and copied consumer DLLs must
match source-owned native packages. Local WMI, owned bitmap/cache, code pages,
CodeDom, SQL connection-string metadata and WCF/Syndication checks run without
Framework fallback. The consumer pins SqlClient4.9.1 as PowerShell does; the
metapackage retains its original4.9.0 minimum. Older framework metadata remains
complete, while older-runtime behavior is unverified. Existing per-library tests
provide broader local coverage; this gate does not establish full remote/cloud,
database or provider compatibility.

SqlClient remains an experimental source port. This metapackage therefore does
not establish that the entire Windows compatibility graph or PowerShell goal is
complete. The runtime2 framework-forwarding defect and its corrective runtime3
clean build are tracked separately; no machine policy or installed runtime files
are patched by this recipe.

Build in MSYS2 CLANG64 with `makepkg --cleanbuild --force --noconfirm`, then audit
the native artifact before installation. `bash check-installed.sh NEW_OUTPUT`
validates installed ownership and another fresh source-feed consumer.
