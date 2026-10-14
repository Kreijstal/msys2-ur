# Windows Community Toolkit notifications 7.1.3

Builds the original desktop notification source from release tag v7.1.3, commit
0ce64d053be11e928408393175851516bd253ccf, against our source-built .NET 8 Windows
Desktop runtime and `Msys2.Windows.WinRT` projection. The NuGet 7.1.3 repository
metadata points to an older December 2020 commit; this recipe instead uses the
actual release tag, whose version.json declares 7.1.3.

The isolated SDK project enables the original NETFX_CORE, WINDOWS_UWP and WIN32
implementation branches. Framework-era registry/reflection/ValueTuple package
references are supplied by .NET 8. SourceLink, SDK.Extras and the upstream
multi-target packaging infrastructure are replaced by the local SDK project.
Native notification activation source is included. No notification features are
stubbed or compiled out. Upstream binary assets are removed and recorded.

`check()` restores the freshly built NuGet package and exercises Unicode
arguments, toast content generation, the real Windows toast object and XML DOM,
notification data maps, and native event registration/removal. It does not show a
toast or register a persistent application identity; delivery and activation of a
running Greenshot application still require an application-level test.
