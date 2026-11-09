# MMI callback declarations and native exports

The installed PowerShell 7.4.20-24 MMI DLL matches its source-built MMI3
3.0.0-18 archive in CLANG64 and UCRT64. Both environments pass 19 independent
native-header signature comparisons covering 14 distinct managed delegates and
74 parameters. This includes all eight operation callback slots, nested reply
and acknowledgement callbacks, session creation/close callbacks, deserializer
class lookup and the Cdecl module entry callback. No declaration mismatch was found.

The C peer reads the actual bridge produced by MMI's SetCallbacks method. Its
72-byte storage has the nine expected offsets, eight populated callback slots
and a null native context (the bridge captures managed context). Disposing the
owned test bridge returns the callback root count to its starting value. The
peer does not invoke provider callbacks.

The installed Windows system libraries expose MI_Application_InitializeV1,
mi_clientFT_V1, MI_Application_NewSerializer_Mof and
MI_Application_NewDeserializer_Mof. The inspector records the actual system
module paths, versions and SHA256 values. Six P/Invoke import policies are
checked separately; export presence and metadata do not prove private codec
prototypes or complete native behavior.

```sh
MINGW_PREFIX=/clang64 bash tests/mmi-callback-abi/check.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/mmi-callback-abi/check.sh NEW_OUTPUT
```

Both fresh runs compiled with zero warnings/errors and exited zero. The
comparator also rejects a deliberately injected Int32 representation of the
one-byte MI_Boolean callback argument. The test uses only installed framework
references; it opens no provider/network connection and changes no services.

See [results and checker hashes](results-20261109.json) and
[text evidence](evidence-20261109/input-identity.json). Earlier storage/export
runs and subsequent signature-comparison logs are retained alongside the fresh
complete runs. Windows output is normalized to LF; recorded source archive,
assembly and system DLL hashes describe the original bytes.
The [cleanup receipt](cleanup-20261109.json) confirms removal of the exact audit
root and staged archives, with installed package versions and MMI hashes retained.

Production code and package releases are unchanged. Private codec tables and
prototypes, authenticated remote CIM/WSMan, broader provider behavior and the
SQL Server/LocalDB/FILESTREAM integration requirements remain open. This audit
does not complete the full dependency goal or authorize binary publication.
