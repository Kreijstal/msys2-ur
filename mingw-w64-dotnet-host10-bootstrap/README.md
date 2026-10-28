# Source .NET10 native host bootstrap component

This CLANG64 package builds native host components from runtime v10.0.5,
commit081d220c0a773ffb7c6bea6b48727833576a65ef. It installs the muxer,
hostfxr,hostpolicy,apphost,nethost,COM host and IJW host, plus headers and
static/import libraries, under `/clang64/lib/dotnet10-bootstrap`.
It does not supply CoreCLR10, managed libraries, reference packs or SDK10.
The installed8.x toolchain remains separately owned.

The port uses Clang/LLD's GNU Windows driver and UASM. Product IJW hosting and
portable native tests remain enabled. The MSVC-only comsxs,ijw and typelibs
test projects remain excluded from this bootstrap build. Compiler flags, CRT
macros, a missing CLR header constant, CET and delay-load linker flags are
adapted without replacing production native implementations.

The exact original Arcade version task from the runtime's pinned VMR dependency
12f41dd0da1a94621e039e27aef264179c1104b5 runs in the installed source.NET8 SDK.
It derives file version10.0.526.11800 from the pinned runtime source date and
passes three upstream vectors. This is a reproducible source-build version,
rather than a claim of an official Microsoft binary build number. Source binary
fixtures are removed before compilation; no vendor SDK/runtime/native binary
is downloaded as a build input.

Checks inspect all seven AMD64 native images and original output hashes,
apphost's actual CET flag, six PE file versions, Unicode-path muxer startup,
nethost buffer sizing/discovery and hostfxr's source version/commit callback.
The original native version and explicit/delay-load nethost tests also run.
No managed runtime or SDK is present in that native API test layout.

Build with the already installed source SDK8.0.131-3, CMake,Clang,LLVM,Ninja,
UASM and Windows/MSYS Python available, then run
`makepkg --cleanbuild --force --noconfirm` in this directory. makepkg downloads
the workflow archive from the msys2-ur release; `python3 make-source.py
<dotnet-mingw-bootstrap checkout>` recreates it byte for byte from
[workflows/runtime10-bootstrap](https://github.com/Kreijstal/dotnet-mingw-bootstrap/tree/master/workflows/runtime10-bootstrap). A private build
directory on a volume with several GiB free is recommended.

This is an intermediate component for PowerShell7.6's source.NET10 graph.
Full CoreCLR/native interop, managed runtime, generators/targeting, SDK/tooling,
WindowsDesktop and PowerShell7.6 dependency/application validation remain open.
