# Windows configuration, drawing and diagnostics from source

This CLANG64 split recipe builds ten separate runtime/NuGet packages from
checksum-pinned dotnet/runtime and dotnet/winforms **v8.0.31** source archives.
The MSYS2 version identifies the source release. NuGet versions retain each
upstream library's servicing version:

| NuGet ID | Version | Package suffix |
| --- | --- | --- |
| Microsoft.Win32.SystemEvents | 8.0.0 | dotnet-systemevents |
| System.Drawing.Common | 8.0.31 | dotnet-drawing-common |
| System.Windows.Extensions | 8.0.0 | dotnet-windows-extensions |
| System.Security.Permissions | 8.0.0 | dotnet-security-permissions |
| System.Diagnostics.EventLog | 8.0.2 | dotnet-eventlog |
| System.Configuration.ConfigurationManager | 8.0.1 | dotnet-configuration-manager |
| System.Runtime.Caching | 8.0.1 | dotnet-runtime-caching |
| System.Diagnostics.PerformanceCounter | 8.0.1 | dotnet-performancecounter |
| System.ServiceProcess.ServiceController | 8.0.1 | dotnet-servicecontroller |
| System.DirectoryServices | 8.0.0 | dotnet-directoryservices |

The generated wrappers preserve upstream conditional C# items. Project
references become exact references to separately built source packages.
Dependencies are recorded in both NuGet and MSYS2 metadata. This includes
System.Drawing.Common for Windows.Extensions' drawing type forwards, and
Security.Permissions for ConfigurationManager/DirectoryServices. The upstream
.NET 8 CAS compatibility implementations are retained; they do not enforce CAS.

All assemblies retain version 8.0.0.0 and their upstream Microsoft/Open
public-signing identities. Resource strings come from upstream resx and SR
sources. Runtime reference projects retain their conditional source items and
forwarders. Drawing's reference contract is derived from upstream
NotSupported.cs, with ColorTranslator/SystemColors forwarded to Drawing.Primitives
as on .NET Core. The runtime package contains the full Windows implementation.

The recipe deletes upstream DLL/EXE/NuGet/library/resource binaries and records
them in removed-binaries.json. In particular, the checked-in EventLogMessages.res
is discarded: GNU windmc builds the 65536 messages from EventLogMessages.mc,
the upstream numeric RC declaration and llvm-rc generate the resource, and the
source-built C# compiler embeds it in System.Diagnostics.EventLog.Messages.dll.
Using the upstream numeric RC is necessary because llvm-rc otherwise treats
windmc's MESSAGETABLE token as a string resource type.

Windows packages expose ref/net8.0 contracts and runtimes/win/lib/net8.0 assets.
The other packages use lib/net8.0. Consumers target plain net8.0, as PowerShell
does. Builds use a new cache with only private/installed source-built feeds.
The currently installed core runtime still uses 8.0.0 sources; these library
packages do not supply its later servicing fixes.

Build in CLANG64, after installing the source-built SDK and
${MINGW_PACKAGE_PREFIX}-dotnet-protecteddata:

```bash
makepkg --cleanbuild --force --noconfirm
```

The package gate compiles upstream contracts, compares public/protected
signatures and type forwards, and tests real Windows operations:

- SystemEvents timer callbacks, cancellation and unsubscription;
- GDI+ drawing, PNG encoding/decoding, font conversion and forwarded types;
- configuration read/save/reopen, Unicode, DPAPI provider and malformed XML;
- cache insertion, expiration and removal callbacks;
- native FormatMessage IDs 0, 1, 42 and 65535 with Unicode substitutions;
- event channels/records/XML/errors and service status/configuration reads;
- built-in performance counter enumeration, uptime and help;
- ADSI WinNT local computer/name/class and DirectorySearcher construction.

Only the private test directory is written. Tests do not register event sources,
write event records, change registry keys, create performance categories, control
services, contact remote directories or change machine configuration. GUI
certificate selection, audio playback, printer operations, remote AD/LDAP and
service/event writes remain outside these checks. The signature gate does not
establish all attribute/layout/generic-constraint or binary compatibility.

Install all ten split packages together, then run a fresh installed consumer:

```bash
bash mingw-w64-dotnet-windows-configuration/check.sh /tmp/windows-configuration-installed
```

The output directory must be new. The default source is the installed feed;
a second argument selects a private package feed for development. NuGet 6.8 may
emit NU5131 when packing ref/runtime-only packages; native and plain net8.0
consumer gates verify Windows asset selection.

Performance counters are tested in a separate process. A native C program first
queries HKEY_PERFORMANCE_DATA without any managed runtime and records Framework
modules loaded by Windows' registered performance providers. The managed counter
check rejects any additional Framework modules; all other checks reject every
Framework module. On win11, Windows loads its installed perfcounter.dll,
mscoreei.dll and sometimes corperfmonext.dll during that native query. These
are existing OS/provider components, not copied package inputs or mandatory
P/Invokes from these libraries. This follows the documented Windows
[provider architecture](https://learn.microsoft.com/en-us/windows/win32/perfctrs/about-performance-counters).
The WMI wminet_utils.dll port remains separate work.
