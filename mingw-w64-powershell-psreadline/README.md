# Source PSReadLine 2.3.6 for PowerShell

The complete Core module is built from PSReadLine tagv2.3.6, annotated tag object
29df75b2560eb8edfc9416b1820c2a14aa345d00, peeled commit
d2e770f93b7a53d8660a6402eb29d1ae1c35e767. Archive SHA256 is
177b308aaa42a360d61c89a33701b840a89c366a98b49104a4d0ba7a9e90954b.
All48 original main C# files,245 resource strings and the original Core Polyfill
source are retained unchanged. The original projects target.NET8 and reference
the complete installed source PowerShell7.4 engine instead of vendor SMA7.2.23.
Pager1.0.0 is restored from the installed source feed and bundled byte-exact.

The module/NuGet version is2.3.6, main assembly2.3.6.0/file2.3.6, Core forwarder
assembly1.0.0.0/file1.0.0.0. Both original informational versions retain the exact
upstream source commit. All457 published public/protected declarations match.
The original five forwarders target sourceSMA7.4.6.500 rather than7.2.22.0; the
Core assembly supplies no legacy prediction implementations. The original
runtime-dependent resolver loads it from net6plus and resolves all five types to
the installed source engine. The original LEGACY/Desktop build is not supplied
by this.NET8/Core package; RuntimeInformation comes from the inbox source runtime.

The published main DLL targets Desktop. Its mscorlib reference must resolve
through complete source runtime facade/CoreLib metadata. Using only the SDK
reference set left Desktop types unresolved and produced a false466-versus457
comparison. No API entries are suppressed in the corrected gate. Vendor DLLs
are read as metadata only, never executed, used as references or packaged.
The source script matches the normalized published script. The published manifest
adds only PrivateData.PSData.ProjectUri; original source manifest fields/bytes
remain intact. The NuGet records the project/repository URL and source commit.

The package supplies a root PSModule NuGet and a loose versioned module: main
DLL, source Pager, net6plus forwarder DLL, original manifest/script/format data,
sample profile, changes and MIT license. Source hashes, project adjustments and
all nine module-file hashes are recorded. It ships no vendor signature, compiler,
engine copy or Desktop fallback DLL.

Fresh build/installed-feed consumers check source inventories, resource contents,
457-entry API/identity, five metadata/runtime forwarders, bundled Pager bytes,
module/GUID/exports and real options/key-handler operations. Nine owned cases
exercise the actual ReadLine loop using unchanged upstream MockConsole.cs:
typing, insertion, backspace, home/end, kill/yank, history, Unicode, Vi editing
and incremental history save. A fresh process reopens and recalls the owned
history file. History writes are confined to the check directory. No keyboard
layout or foreground window is changed. The complete upstream xUnit suite,
broader completion/prediction/help behavior and actual terminal/ConsoleHost
integration remain unverified by these console-model checks.

Build/check in CLANG64:

```bash
makepkg --cleanbuild --force --noconfirm
bash check.sh NEW_OUTPUT PINNED_SOURCE
```

Each check output directory/cache is fresh and external feeds are cleared.
The actual runtime is.NET8.0.0; SDK8.0.131/reference aliases do not supply later
runtime servicing fixes. Shipping pwsh/full SDK integration remains separate.
