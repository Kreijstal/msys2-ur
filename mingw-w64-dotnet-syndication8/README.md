# Syndication 8 for the source-built .NET feed

Builds System.ServiceModel.Syndication 8.0.0 from dotnet/runtime v8.0.31.
Assembly version 8.0.0.0 and file version 8.0.31.0 identify the actual source.
The Open public key preserves the cc7b13ffcd2ddd51 assembly identity; public
signing does not claim an upstream private-key signature.

This package coexists with dotnet-syndication (10.x). WCF 4.10.3 needs the
8.x assembly for its legacy System.ServiceModel forwarding shim, and
Windows.Compatibility 8 also requires this NuGet version. It does not replace
or relabel the existing 10.x package.

The upstream project compile items and reference contract are retained.
Source binary inputs are removed. Neutral resources are rebuilt. This source archive contains no Syndication
XLF translations; the helper also preserves XLF files when present. No published implementation binaries are used.

The check gate compares public/protected API signatures with the source-built
upstream contract and restores a fresh consumer from the newly built feed.
It checks Atom/RSS roundtrips with Unicode, dates, links and XML extensions,
AtomPub service documents, malformed XML, exact resource strings and assembly
identity/source/location. These checks do not establish every formatter edge
case or complete binary compatibility.

After installation, run in CLANG64 with a new output directory:

```bash
bash check.sh /tmp/syndication8-installed $MINGW_PREFIX/share/doc/dotnet-syndication8/localization.json
```
