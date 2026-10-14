# Source-built WinRT bootstrap for .NET 8

This CLANG64 package builds three pieces from source:

* `Windows.winmd`, containing 14,755 WinRT definitions, compiled from Microsoft's
  checked-in textual RDL declarations in windows-rs;
* the native `cswinrt.exe` generator and the strong-named `WinRT.Runtime.dll`;
* `Msys2.Windows.WinRT` 0.1.1, an offline NuGet package containing the generated
  `Microsoft.Windows.SDK.NET.dll` projection for the 2,058 types selected by
  `metadata-main.rs`, including their transitive dependencies.

The runtime NuGet package is `WinRT.Runtime` 2.3.2-msys2.20261015. Its assembly
version, 2.3.1.0, follows the pinned source's build variables. Use this feed from
our source-built .NET 8 SDK. This is a bootstrap subset, not a replacement for
all versions or all APIs in Microsoft's Windows SDK contract/reference packages.
Consumers porting from .NET Framework should replace the old
`Microsoft.Windows.SDK.Contracts` reference with `Msys2.Windows.WinRT`.

The selected surface covers Greenshot's notification, OCR, graphics capture,
Direct3D interop, XML, globalization, data transfer, video encoding, accent settings, package management and stream APIs. The installed
`share/dotnet-winrt/projection-types.rsp` records the exact included and excluded
types. The full generated metadata and generator are installed for extending the
projection later. The CLI does not automatically reference this custom subset
when a Windows SDK TFM is selected: add the explicit NuGet reference.

## Bootstrap inputs

All three repositories and the four Rust source crates are hash-pinned in the
recipe. `prepare.py` removes upstream DLLs, executables, WinMD and other compiled
artifacts and records their paths and hashes in `removed-binaries.json`. The
Rust reader's binary-default metadata feature is disabled; its dependency on
`windows-default` is removed. Cargo uses only vendored source and `--frozen`.
.NET restore uses the empty NuGet source configuration and the locally built
feed. No Windows SDK download, binary NuGet seed, MSVC or MIDLRT is used.

`0001` repairs the RDL emitter's generic event signatures, split property rows,
static/composable class flags and activatable default constructors. Method order
is preserved, including accessors separated in the source to preserve vtable
slots. `0002` uses standard C++ containers and synchronous generation instead of
Microsoft's PPL, adds missing standard headers, and fixes a dangling lambda
capture. `additions.py` includes upstream C# support sources for namespaces
selected by individual types.

## Validation

`check()` consumes the freshly packed NuGet artifacts and calls Windows for
metadata queries, XML and Unicode, asynchronous native stream reads/writes,
bitmap allocation and OCR, and the graphics-capture support query. OCR requires
an installed recognition language. On the current host OCR uses `en-GB`.
The Windows capture service is absent: the support query returns 0x80070424;
this condition is reported explicitly and verifies HRESULT propagation, while
actual capture remains untested. Other unexpected COM errors fail the check.

The notification toolkit is packaged separately and tests native toast XML,
property maps and event registration. These checks do not display notifications
or register a persistent application identity.
