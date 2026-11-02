# Original runtime10 GenFacades bootstrap

Builds all eight unchanged Core GenFacades task sources from the exact Arcade
commit used by runtime10.0.5, including partial facade generation, unsupported
API generation and assembly reference version clearing. All four original
MSBuild target files are preserved. Installs to an isolated tool-pack folder.

The bootstrap targets NET8 with installed SDK8 MSBuild17.8.49 and source-built
Roslyn4.14. The original NET10/net472 hosts, exact declared Roslyn4.8 and
MSBuild17.12.50 closure remain open. This bootstrap supplies the original task
implementation for the runtime10 framework build; it does not complete the
runtime, SDK, PowerShell7.6 or full dependency-porting goal.
