# OpenTerminal package status

This package contains the current x86-64 UCRT OpenTerminal deployment for
native Windows. It is not an official Microsoft Windows Terminal build and is
not yet a complete, general-purpose terminal emulator.

The source project generates this deployment on Linux with a MinGW pipeline
that runs some Microsoft SDK and XAML build tools through Wine. Wine is a build
and Linux-validation tool only; it is not a runtime dependency of this MSYS2
package and no Wine or OpenXaml runtime is included.

The PKGBUILD repackages a generated, checksummed bundle published as a release
asset because the complete host build currently requires those Wine-hosted
tools and a .NET Framework 4.8 prefix. The bundle keeps these native Windows files
together because `wt.exe` and `elevate-shim.exe` locate
`WindowsTerminal.exe` beside themselves:

- `WindowsTerminal.exe`, `wt.exe`, and `elevate-shim.exe`;
- the three UCRT MinGW runtime DLLs used by that exact build;
- the four Cascadia deployment fonts; and
- all generated Terminal XBF files in their namespace-relative directories.

The small package patch records the resource-scope fix used to complete the
pinned source snapshot's native smoke-test build. The bundle integrity manifest
binds every deployed file and path to the package checksum.

Beside the bundle the package installs `Microsoft.UI.Xaml.dll`, which is
OpenTerminal's own `phase3/xamlcore` runtime cross-compiled from the same pinned
commit with mingw-w64 GCC. No Microsoft binary is redistributed. `WindowsTerminal.exe`
activates nine WinUI 2 classes that are not part of Windows, so without this the
process aborts before its first window with
`winrt::hresult_class_not_registered`. The file carries the lookup name rather
than its own because C++/WinRT finds an unregistered class by trimming the class
name and loading the namespace-named DLL; `Windows.UI.Xaml.*` still resolves to
the system implementation.

The package also installs `WindowsTerminal.exe.manifest` beside the exe. The
bundled exe has no embedded manifest of any kind, and XAML Islands refuses to
start for a host process that declares no tested Windows version:
`WindowsXamlManager::InitializeForCurrentThread()` fails `E_UNEXPECTED` with
"supported for apps targeting Windows version 10.0.18226.0 and later". Windows
consults `<exe>.manifest` only when the binary carries no embedded one, which is
what makes the external file work here; upstream the declaration belongs in the
link step, as `phase3/harness/xaml_probe.manifest` already is for the probes.

Windows system components are deliberately not bundled or replaced. In
particular, the package does not ship `d2d1.dll`, `d3dcompiler_47.dll`,
`Windows.UI.Xaml.dll`, or API-set forwarding DLLs; normal Windows resolves
those components from the operating system.

With both files in place the process gets through WinUI 2 activation and through
XAML Islands initialization, and then stops in `App::InitializeComponent()`:
`Application::LoadComponent` on `TerminalApp/App.xbf` fails `0x802B000A`. That is
the gap `phase3/xamlcore`'s own README records - Terminal's `App.xaml` resolves
against `XamlControlsResources`, whose theme resources and merge semantics live
in the layout core but are not yet served through the WinUI 2 activation surface.
So this package does not yet reach a window. `phase3/xamlcore` is validated
upstream as the whole XAML stack under Wine, not as a WinUI 2 half beside the
Windows one, and that difference is where it currently stops.

The pinned OpenTerminal snapshot has no top-level license declaration. The
installed `OpenTerminal-NO-LICENSE.txt` records that fact and does not create a
license grant; resolve that before redistributing this experimental package.

Running OpenTerminal on Linux is a separate integration scenario. Use the
pinned Phase 4 procedure and `Kreijstal/wine-kreijstal` with an externally built
OpenXaml runtime; do not add those Linux compatibility components to the native
MSYS2 package.
