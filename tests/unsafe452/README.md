# Unsafe 4.5.2 source bootstrap

This builds the original `System.Runtime.CompilerServices.Unsafe` 4.5.2 assets from CoreFX commit `02b11eeee1fbc5f3ef43a1452fe07efd25fa1715`. The source pin is present in the published native VERSIONINFO. Published DLLs are read only as metadata; none is executed or used as a compiler reference.

The package preserves all three runtime profiles (`netstandard1.0`, `netstandard2.0`, `netcoreapp2.0`) and both compiler reference profiles (`netstandard1.0`, `netstandard2.0`), assembly version `4.0.4.1`, public key token `b03f5f7f11d50a3a`, the original dependency groups, XML documentation and licenses. The original IL, include headers and reference C# are unchanged. Source-built ILAsm10 assembles the runtime assets; a source-built Csc4.4 CLI emits the references using source reference contracts. This is a disclosed bootstrap, not a replay of the historical BuildTools environment.

The native version resource is reconstructed using source LLVM RC/CVTRES. Original publisher version strings (including the historical `@BuiltBy` value) are retained as compatibility metadata. They describe the original version, not the machine producing this bootstrap; `results.json` and `compiler44-source-inputs.json` record the actual build inputs. Runtime managed file/informational versions remain the original IL's `4.0.0.0`; reference versions retain `4.6.26919.02` and its original source annotation.

Validation compares every profile's 35 public API entries, assembly identity, dependency identities, managed product/version metadata, reference marker, and all native VERSIONINFO fields with published metadata. Every public IL method body is compared with the original instruction stream. All 34 public methods execute through a fixture in an isolated load context that requires the exact old candidate DLL. Checks cover pointer/reference aliasing, offsets, aligned/unaligned operations, guard bytes and zero-length controls.

A fresh `netstandard2.0` PackageReference consumer must restore the exact source archive, select `ref/netstandard2.0` for compilation and `lib/netstandard2.0` for execution, and run the same fixture against that isolated runtime asset. Historical runtime testing and the complete old Standard1.0 NuGet dependency closure remain open. This package is one prerequisite for the original Roslyn3.4/ReferenceAssemblyAnnotator build chain; it does not complete that chain or the PowerShell dependency goal.

Producer validation:

```
python3 build.py CORE_FX_ARCHIVE NEW_PRODUCER CSC44_DIRECTORY
python3 pack.py PRODUCER
python3 audit.py PRODUCER
python3 check.py PRODUCER NEW_CHECK CSC_DIRECTORY --feed PRODUCER/feed
```

Installed validation uses the documented producer record plus `--feed /clang64/lib/dotnet/library-packs`; the checker takes every DLL from the specified package archive.
