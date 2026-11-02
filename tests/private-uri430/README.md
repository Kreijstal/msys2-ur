# System.Private.Uri4.3.0 metadata source port

The original package contains no DLL. This port preserves its exact empty
ref/netstandard marker, licenses, dependency IDs and1.1.0 minimum versions,
using the original CoreFX4d1af962ca0fede10beb01d197367c2f90e92c97 package project.
The project keeps PreventImplementationReference=true and separate Windows/Unix
provider project references. No replacement implementation or provider is added.

Fresh Standard1.3 and NETCore5.0/aot restores use the installed source feed with
new caches. The checker verifies every original data byte, exact dependency
versions and the absence of compile/runtime DLL assets. This completes the
carrier package only. Runtime-specific URI implementations and the full
PowerShell dependency goal remain separate requirements.
