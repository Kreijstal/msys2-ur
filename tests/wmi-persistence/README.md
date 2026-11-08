# Source WMI persistent writes

Run in CLANG64 or UCRT64 on the Windows packaging host, with the installed
source-built System.Management package and SDK:

```sh
bash tests/wmi-persistence/check.sh NEW_OUTPUT
```

The fresh consumer restores only the installed source feed and compares the
restored archive, managed implementation and native helper bytes. Separate STA
and MTA threads each create a unique `root\MSYS2_WmiPersist_<GUID>` namespace,
persist a keyed class and instance, reopen their schema/data, update Unicode
and UInt32 values, query the stored result, await asynchronous Put, force GC,
reopen the stored instance, and delete the instance, class and namespace.
Namespace deletion also runs in `finally` when a check fails. The process must
load `msys-wmi-native.dll` and must not load Framework implementation/helpers.

The synchronous Put path exercises the original semisynchronous
`IWbemCallResult` handling. The asynchronous path exercises the source backend's
sink and completion callbacks. `ObjectPut` supplies a **class path** in this
original implementation; the fixture records that behavior and reopens the
instance with its saved keyed path. `FrameworkPathControl.ps1` independently
confirms the class-path behavior with Windows' built-in System.Management,
using its own temporary namespace. This control is separate from the source
consumer and does not change the build target or package dependencies.

This gate covers local static repository classes. Remote/domain credentials,
delegation, other providers, complete native ownership and callback race
coverage remain open. The complete PowerShell dependency goal stays incomplete.

The original PowerShell integration fixture runs from the installed console:

```sh
pwsh.exe -NoLogo -NoProfile -NonInteractive -STA -ExecutionPolicy Bypass -File tests/wmi-persistence/PowerShellPersistence.ps1
pwsh.exe -NoLogo -NoProfile -NonInteractive -MTA -ExecutionPolicy Bypass -File tests/wmi-persistence/PowerShellPersistence.ps1
```

PowerShell 7.4.20-9 in both environments passed **14 checks per mode**, using
original New/Set/Get/Remove-CimInstance cmdlets with local default and explicit
DCOM sessions, and source System.Management reads of the same repository data.
The bundled managed implementations must match their installed source archives.
Each run deletes its own namespace.
[Application build, installed logs and hashes](../powershell-mmi/instance-clone-integration-results-20261108.json)
record the exact application revision.
