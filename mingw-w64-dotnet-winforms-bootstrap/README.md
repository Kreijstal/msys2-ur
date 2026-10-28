# WinForms source bootstrap for .NET 8

This interim package builds **WinForms 7.0.20 source on .NET 8**, together with
Drawing.Common 8.0.0 and its runtime dependencies. It installs the explicitly
labelled framework `8.0.0-bootstrap.7.0.20`, reference/runtime packs, the upstream
application configuration generator, and WindowsDesktop SDK XML for WinForms.

WinForms 8 itself is still pending its source-built CsWin32/Win32Metadata pipeline.
This package does not provide WPF, the WinForms design assemblies, or localized
satellite resources. Its assembly versions are 8.0.0.0 for this bootstrap port;
`source-bootstrap.json` records the upstream source releases.

The Microsoft build inputs are pinned source archives. Executable upstream test
fixtures are deleted before compilation. The installed source-built .NET SDK,
reference pack, interop generators, and ilasm are used; the trusted MSYS2 UCRT64
Mono seed supplies the resource compiler and the small source-built resource
helper. No Microsoft binary SDK/runtime, NuGet package, WinMD, or compiler download
is used. WPF source supplies SDK XML only.

The driver scripts come from commit 3ae98d5 of
https://github.com/Kreijstal/dotnet-mingw-bootstrap (newer WinForms work lives
in https://github.com/Kreijstal/wpf-mingw). Run `MSYSTEM=CLANG64 makepkg-mingw -s`. The source-built bootstrap SDK/runtime/ilasm
packages must be installed first. `check()` builds with an empty NuGet feed and
opens/closes a real form on an interactive Windows desktop, both as a shared
framework application and a self-contained publish. It checks controls, events,
embedded resources, GDI+ pixels, and `ApplicationConfiguration.Initialize()`.

A project can use the usual SDK settings:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0-windows</TargetFramework>
    <OutputType>WinExe</OutputType>
    <UseWindowsForms>true</UseWindowsForms>
  </PropertyGroup>
</Project>
```

For an application with no NuGet dependencies, clear package sources in
`NuGet.config` and build with `dotnet build`. A standalone Windows application can
be created with `dotnet publish -r win-x64 --self-contained true`.

This is a compatibility bootstrap, not a supported upstream .NET 8 WinForms
release. The .NET 7 resource/ActiveX paths retain their upstream BinaryFormatter
code; applications that use these paths need the corresponding runtime setting.
