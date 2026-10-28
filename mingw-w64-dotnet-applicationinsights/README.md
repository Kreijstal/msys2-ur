# Application Insights core 2.23.0 from source

Builds Microsoft.ApplicationInsights from release commit
2faa7e8b157a431daa2e71785d68abd5fa817b53, confirmed by the official 2.23.0 nuspec.
Source SHA-256: d4db350c94a29d41ac58a62f53d86fc6124a458904ccf6f607c1eca2f8d023a0.
The standalone net8.0 build retains the original netstandard2.0 source feature
branches and PUBLIC_RELEASE symbol, all core C# files and the public signing key.
It uses the already source-built DiagnosticSource 8.0.1 selected by PowerShell.

Assembly identity is 2.23.0.29 / 31bf3856ad364e35, matching upstream. Source
informational version is 2.23.0 plus commit. The release's build-number metadata
was read with PEReader/System.Reflection.Metadata only; no published DLL was
loaded, executed, compiled against or used as a package payload. Public signing
does not claim a Microsoft private-key signature.

Source implementation binaries, test binaries and signing-key blobs are removed.
The adapter uses only the public key already present in the source AssemblyInfo.
SourceLink, development analyzers and EventRegister are build-only tooling;
upstream core EventSource and telemetry implementations remain in the assembly.
It does not ship the separate web, server-channel or platform integration packages.
The core runtime remains built from 8.0.0 sources.

The gate restores a fresh source-feed consumer and checks all 1,033 upstream
PublicAPI declarations using source-built Roslyn. It checks source identities/
versions/locations and exercises event, trace, exception, metric, request and
dependency telemetry, operation/parent correlation, telemetry initializers,
JSON/gzip serialization, clone isolation, disabling and flushing. Its recording
channel keeps every telemetry item in memory; it sends no telemetry externally.
The older instrumentation-key constructor is deliberately checked, producing one
upstream deprecation warning. Network ingestion, retry/failover, ETW registration,
all metric aggregation and actual PowerShell integration remain unverified.

In CLANG64:

```bash
PATH=/usr/bin:/clang64/bin:$PATH makepkg --cleanbuild --force --noconfirm
bash check.sh /tmp/applicationinsights-installed
```

Roslyn is used only by the validation gate, not as a runtime package dependency.
Published identity provenance is recorded in
[applicationinsights-published-identity-20261026.json](https://github.com/Kreijstal/dotnet-mingw-bootstrap/tree/master/workflows/powershell-deps/applicationinsights-published-identity-20261026.json).
