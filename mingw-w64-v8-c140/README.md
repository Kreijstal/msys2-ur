# V8 for Chromium 140 consumers (UCRT64)

`mingw-w64-ucrt-x86_64-v8-c140` is V8 **14.0.365.10**, the engine shared by
the Chromium 140 generation: Chromium **140.0.7339**, Electron **38** and Qt
WebEngine **6.11.2**. It uses the V8 sources from Qt's checksum-pinned source archive,
including Qt's security backports. The original V8 DEPS revision is
`b7ed978e41b4bac7802b206404d0e2f3d09f31ac`; Qt's Chromium revision is
`5170777d28bee1ce92cc693a0dbf2ad01492e5cf`.

The initial target is native Windows x64, GCC and the UCRT64 runtime. The
`c140` slot names its DLLs and directories, so it installs beside the
distribution's newer `v8` package. Patch 027 adds GN's
`component_output_suffix`, which appends `-c140` to every component DLL.
Patch 028 is Electron 38's only V8 change: a per-context microtask policy. It
adds virtual methods to `v8::MicrotaskQueue`, so every consumer compiles
against these headers; the SDK gate enforces that.

## Build

In an MSYS2 UCRT64 shell:

```sh
cd mingw-w64-v8-c140
makepkg-mingw -s
```

`V8_BUILD_JOBS` controls parallel compilation (default 4). `abi-profile.gn`
contains the common engine configuration for shared and monolithic builds.
Both use the same eight-file jumbo compilation limit as the Qt control.
ICU data comes from the system ICU data DLL, matching the Chromium control;
the package does not require a separate `icudtl.dat` file.
The static archive retains ICU, WebAssembly, pointer compression and sandbox
support. Native Python extracts the inputs, and directory junctions make the
source dependencies visible to native GN, Ninja and Python.

The existing MSYS2 V8 MinGW patches provide the toolchain and platform port.
All 17 patches were compared against the official MSYS2
[V8 recipe](https://github.com/msys2/MINGW-packages/tree/5536714fa8c7c9d0953d875fab6c52d475df9b7a/mingw-w64-v8).
Thirteen are unchanged. Patches 001, 012, 014 and 015 are adapted to the older
Chromium-matched source: build-toolchain differences, DLL exports, Windows
register scanning and Abseil build differences respectively. The DLL export
adaptation preserves out-of-line symbols needed by Chromium and removes the
import attribute from the inline cppgc default platform.
The additional Perfetto patch comes from the existing WebEngine MinGW port.
The Abseil compatibility patch also matches that port's private headers and
Windows thread-local storage implementation. Official release definitions are
part of the SDK interface because they change private V8 declarations.
The Qt archive and local build inputs have SHA-256 checksums. Gitiles changes
tar entry timestamps on each download, even at a fixed commit; `unpack.py`
therefore verifies every dependency's complete payload against
`source-trees.json` before extraction. This SHA-256 identity includes paths,
entry types, modes, link targets and file contents, excluding only volatile
timestamps and ownership metadata. `SKIP` in the recipe applies only to those
unstable compressed archive bytes, not to their contents.

## Installed interface

* `bin/libv8-c140.dll`, `libv8_libbase-c140.dll`, `libv8_libplatform-c140.dll`
  and the tracing runtime `libv8_libperfetto-c140.dll`.
* Their import libraries and `libv8_monolith.a` under `lib/v8-c140`, built
  with the same engine feature configuration.
* `d8`, `torque`, `torque-language-server` and `mksnapshot` under
  `lib/v8-c140/bin`.
* Public headers under `include/v8-c140`, plus private and generated headers
  under `share/v8-c140/chromium-sdk`.
* `share/v8-c140/build-manifest.json`, including the slot, resolved flags,
  public/private definitions, source identities and payload checksums.
* `share/v8-c140/snapshot_blob.bin`, generated alongside the embedded snapshot
  by the same upstream `mksnapshot` invocation.
* pkg-config modules `v8-c140`, `v8_libbase-c140`, `v8_libplatform-c140`,
  `cppgc-c140` and `v8_monolith-c140`. The modules expose `sdkdir`, `manifest`, `d8`, `torque`, and
  `mksnapshot` and `snapshot_blob` variables.

cppgc and heap-base implementations live in **libv8-c140.dll**. `cppgc-c140.pc` links
that real implementation. The package does not build a second collector DLL
with duplicate GC globals. Shared consumers get Windows import definitions;
`v8_monolith-c140.pc` omits them. Automatic package stripping is disabled so payload
hashes remain valid after installation.
The monolithic module selects its separately generated non-component Perfetto
header under `share/v8-c140/static-include`; shared clients keep the DLL configuration.

See [the integration](INTEGRATION.md) and
[acceptance checks](../tests/v8-chromium/README.md). Binary publication requires
the installed-SDK and bundled/system `content_shell` checks to pass.
