# EventTraceKit resource compiler for .NET 8

This packages the MIT-licensed EventTraceKit event manifest parser, message
writer and WEVT_TEMPLATE compiler from commit
`f919e38bbf553f89058f98b5d1eeb3c4536a673b`. The small command-line driver accepts:

```
event-manifest-compiler EVENTMAN_XSD WINMETA_XML MANIFEST OUTPUT_BASE
```

It generates `.rc`, `.wevt.bin` and localized `.msg.*.bin` resources. It does not
implement the upstream Visual Studio extension, MEF discovery, C++ header
generation or the upstream `emc` command-line interface. The underlying upstream
resource compiler is retained. The .NET 8 port removes MEF registration metadata
and the obsolete null `MemoryMappedFileSecurity` argument; default OS security
and the original mapping ownership are retained. Legacy serialization/CER/CAS
annotations produce 25 compiler warnings on .NET 8.

The build restores with no NuGet sources or downloaded assemblies. The schema
and Windows metadata XML are explicit caller inputs and are not included in this
package. PowerShell's native recipe pins those build-time text inputs from the
public microsoft/win32metadata source repository; its license disclaimer leaves
the SDK input files under their original SDK licenses.

The native PowerShell recipe checks these generated resources through Windows
TDH without installing an event provider. This tool requires the source-built
CLANG64 .NET 8 runtime.
