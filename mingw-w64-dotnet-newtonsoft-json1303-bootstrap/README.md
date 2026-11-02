# Newtonsoft.Json 13.0.3 source bootstrap

The exact NuGet7.3 dependency builds from the upstream13.0.3 tag archive, SHA256
3dc1eeeb8f781122e0713481bad993329c669feb9928cc4ec86e0ab24d9eff9e.
All233 original C# files and the original NETStandard2.0 defines are retained.
The source-built113-asset NETStandard.Library2.0.3 reference contract is used.
Assembly version13.0.0.0 and public key30ad4fe6b2a6aeed follow upstream.
The original Build/build.ps1 date formula supplies the file version; the build
uses UTC and honors SOURCE_DATE_EPOCH. InformationalVersion marks this source
bootstrap. No published implementation or reference binary is downloaded.

Checks verify source hashes, original identity/TFM, typed/Unicode/dynamic/JSON-path
and XML roundtrips, plus the unchanged upstream ToStringEnsureEscapedArrayLength
and PopulateObjectWithHeaderComment regression methods. An installed consumer
extracts the exact installed NuGet asset into a new directory and repeats the
runtime checks after verifying the complete package payload manifest.

This supplies the original NS2 runtime profile only. Other original framework
profiles, full upstream tests, original analyzer/package validation and SourceLink
build-tool integration remain open. This package does not complete NuGet7.3,
SDK10 or the full PowerShell dependency goal. Newtonsoft13.0.4 remains available
as a separate version in the source feed.
