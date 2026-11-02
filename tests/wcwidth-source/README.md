# Original Wcwidth.Sources packages

The SDK10 template CLI explicitly copies the net6.0 content of Wcwidth.Sources
2.0.0 into its NET10 build. Spectre.Console0.54.0 separately requires the private
source dependency Wcwidth.Sources4.0.1. Keep both versions and their original
source content profiles; do not replace the SDK's older source with the newer
version.

Both packages are exported from the exact Git commits in their release nuspecs.
All original C# content bytes match the release source archives. Version2.0.0
contains seven original files under each of net8.0/net7.0/net6.0/netstandard2.0;
4.0.1 contains nine under each of net10.0/net9.0/net8.0/netstandard2.0. Production
source is unchanged, including the original visibility and warning directives.
The checked-in Unicode tables are retained: the original production project
includes these files and does not invoke the developer table generator.

Validation compiles source content with Csc5.3 on source NET10, executes unchanged
upstream Fact method bodies through an explicit small assertion/Fact adapter,
and rejects an intentionally failing assertion. It also compiles real NS2
consumers with public and internal visibility, then executes their scalar and
Unicode-version cases on NET10. Fresh NuGet/Roslyn task checks preserve the SDK's
ExcludeAssets=all/net6.0 source-copy behavior for2.0.0 and the automatic content
compile items for4.0.1. Every published content profile is shipped; there is no
claim that all corresponding historical runtime hosts were executed.

The original MinVer, NuGetizer, SourceLink and analyzer toolchain has not been
replayed. The explicit source packaging port preserves package identities and
all content rather than distributing a prebuilt binary. Full SDK10/PowerShell
and the broader dependency goal remain open.
