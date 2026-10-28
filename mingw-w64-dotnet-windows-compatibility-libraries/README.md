# Remaining Windows compatibility libraries for .NET 8

Nine split packages build the missing satellite libraries required by
Microsoft.Windows.Compatibility 8.0.31, using dotnet/runtime v8.0.31 sources:

| NuGet ID | NuGet version |
| --- | --- |
| System.CodeDom | 8.0.0 |
| System.Reflection.Context | 8.0.0 |
| System.ComponentModel.Composition | 8.0.0 |
| System.ComponentModel.Composition.Registration | 8.0.0 |
| System.Data.Odbc | 8.0.1 |
| System.Data.OleDb | 8.0.1 |
| System.DirectoryServices.AccountManagement | 8.0.1 |
| System.IO.Ports | 8.0.0 |
| System.Speech | 8.0.0 |

Assembly versions remain 8.0.0.0; file versions identify source release
8.0.31.0. The Open, ECMA and MicrosoftShared public keys preserve their upstream
identities. Public signing does not claim an upstream private-key signature.
The underlying core runtime is still built from 8.0.0 sources.

The adapter retains upstream conditional compile items, embedded metadata XML,
Speech's original SR/SRID resources and seven phoneme mapping data files. Source
binary implementations are removed. No downloaded implementation DLL is used.
Project references become explicit source-built NuGet dependencies. The Windows
libraries expose rebuilt upstream contracts in ref/net8.0 and implementations in
runtimes/win/lib/net8.0 so plain net8.0 consumers select functional assets.
The other libraries use lib/net8.0. NU5131 warns about the explicit reference/
runtime layout; consumers verify actual selection. Build order follows the
MEF/Reflection.Context dependency graph.

The check gate compares 4,339 upstream public/protected API signatures, then
restores a fresh consumer with plain net8.0. Behavioral checks cover:

- CodeDom C# generation, compilation/execution with source-built Roslyn, VB
  generation and identifier validation;
- attributed and convention MEF composition, imports, shared lifetimes, missing
  exports and custom reflection properties;
- native ODBC driver-manager diagnostics for a unique nonexistent driver,
  parameter types and failed-open cleanup;
- native OLE DB COM provider enumeration, metadata, connection strings and
  parameters, using Windows' SQLOLEDB provider;
- read-only local SAM user/SID lookup and group enumeration;
- serial-port registry enumeration and native CreateFile failure/cleanup for a
  nonexistent port;
- SRGS grammar XML roundtrip/binary compilation and native SAPI speech synthesis
  to an in-memory WAV, with an enabled Windows voice;
- all nine source identities/versions/locations and exported types, all 967
  neutral resource strings, and no .NET Framework implementation modules after
  the native operations.

These tests do not establish database query interoperability, physical serial
I/O, remote Active Directory/domain authentication, microphone recognition,
all MEF configurations, or full binary compatibility. Tests require Windows'
built-in SQLOLEDB/SAPI facilities and an enabled speech voice; no extra service,
DSN, certificate store, registry or account configuration is installed or changed.
Windows' native OS components supply ODBC, OLE DB, ADSI/SAM and SAPI facilities.
Roslyn is used by the test gate only and is not a package runtime dependency.

In CLANG64, with the source-built SDK and declared dependencies installed:

```bash
PATH=/usr/bin:/clang64/bin:$PATH makepkg --cleanbuild --force --noconfirm
```

After installing all nine split packages, use a new output directory:

```bash
bash check.sh /tmp/compatibility-installed /clang64/share/doc/dotnet-codedom/localization.json
```

The dependency graph evidence is in
[windows-compatibility-graph-20261026.json](https://github.com/Kreijstal/dotnet-mingw-bootstrap/tree/master/workflows/powershell-deps/windows-compatibility-graph-20261026.json).
The overall PowerShell dependency and native-port objective remains incomplete.
