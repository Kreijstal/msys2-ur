# Source PowerShell Pager 1.0.0

Both original C# production files are retained unchanged from PowerShell/Pager
v1.0.0, commit965675f549dfa074eb02a47ca6d6e07d0ee7771f. The original project
targets.NET8 in this CLANG64 port. There are no runtime NuGet dependencies.
Assembly1.0.0.0/file1.0.0.0/informational1.0.0 and all three published public API
declarations match the metadata-only baseline. Vendor binaries/signatures are
never used as build inputs, executed fixtures or package payload.

The source NuGet supplies lib/net8.0/Microsoft.PowerShell.Pager.dll, the original
MIT license, source inventory and this README. The installed consumer uses a
fresh NuGet cache with external feeds cleared. It checks source hashes, exact
metadata identity/API, installed NuGet bytes and all four upstream rendering/
scrolling/regular-expression cases using the unchanged original TestConsole.
Four xUnit discovery attributes are removed and four string-equality calls use
an owned ordinal assertion. The original test bodies, inputs and expected output
remain; no substitute xUnit implementation is provided. This is console-model
unit coverage, separate from full interactive terminal integration in PSReadLine.

```bash
makepkg --cleanbuild --force --noconfirm
bash check.sh NEW_OUTPUT PINNED_SOURCE
```

The actual runtime is.NET8.0.0; SDK8.0.131 is not a later servicing-runtime build.
