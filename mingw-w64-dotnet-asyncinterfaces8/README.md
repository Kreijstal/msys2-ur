# AsyncInterfaces 8 for PowerShell's .NET 8 dependency graph

Builds Microsoft.Bcl.AsyncInterfaces 8.0.0 from the ten upstream ref-directory
type-forwarding declarations in dotnet/runtime v8.0.31. .NET 8 already supplies
the implementation types; this is the upstream facade design for frameworks
starting with .NET Standard 2.1. No downlevel implementation types are redefined.

The separate package coexists with the existing AsyncInterfaces 10 recipe.
Assembly version is 8.0.0.0, file version 8.0.31.0 and source informational
version 8.0.0+runtime-v8.0.31. The Open public key preserves cc7b13ffcd2ddd51;
public signing does not claim an upstream private-key signature.

A fresh consumer checks all ten root forwards plus the nested enumerator, exact
identity/source/location and resolution to the source-built inbox. It exercises
real async enumeration, configured awaits, disposal and cancellation. These
checks do not prove every downlevel framework or full binary compatibility.
The core runtime remains source-built from 8.0.0, regardless of tooling aliases.

In CLANG64:

```bash
PATH=/usr/bin:$MINGW_PREFIX/bin:$PATH makepkg --cleanbuild --force --noconfirm
bash check.sh /tmp/asyncinterfaces8-installed
```
