# Original source CoreCLR10 native bootstrap

Builds runtime10.0.5 CoreCLR, RyuJIT and two native resource DLLs through the
frozen 64-file MinGW port. Original cDAC generator sources and the exact VMR
System.CommandLine2.0.4 dependency compile with the installed source Compiler5
and SDK8. The descriptor is generated from original native layout data rather
than a stub. Exact patch replay, native inputs, source versions and loaded
cDAC descriptor bytes are audited.

Installation is isolated under `lib/dotnet-bootstrap10/coreclr/10.0.5` and does
not register a shared framework or replace the active NET8 runtime. Native
checks cover original JIT startup/ABI, Unicode paths, four source PE versions,
real cDAC content and eleven EHa cases/200000 stress rounds. These checks do not
establish managed CoreLib execution or complete runtime compatibility.

Matching source CoreLib and complete managed framework, native DAC/debugger,
ETW registration, EHa foreign/hardware unwind cases, ReadyToRun/AOT, final
runtime/targeting/SDK/desktop10 and PowerShell7.6 plus earlier compatibility
gates remain open. The cDAC host is an explicit NET8 bootstrap port of the
original NET10 tool target. Full original host profiles remain part of the goal.
