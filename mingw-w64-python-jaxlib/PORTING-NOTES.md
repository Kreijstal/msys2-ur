# jaxlib on MSYS2 MinGW (ucrt64) — porting notes

## Status

Working. `makepkg-mingw` of this recipe builds jaxlib 0.11.2 (CPU) with
Bazel 8.7.0 and MSYS2 clang 22 / lld; check() passes; the packages
mingw-w64-ucrt-x86_64-python-jaxlib 0.11.2-1 and -python-jax 0.11.2-1 are
installed on win11. Verified with the installed packages (2026-10-07):
- `import jax` -> 0.11.2, `jax.devices()` = [CpuDevice(id=0)]
- jnp ops, jax.jit, jax.grad, jax.vmap, random, linalg (qr, eigh, solve,
  svd), lax.conv, fft, scan, while_loop, bf16/f16
- a 8-64-64-1 MLP trained with jit(value_and_grad) + SGD: loss 2.456 ->
  0.020 in 1000 steps (0.4 s)
- wheel tag cp314-cp314-mingw_x86_64_ucrt_gnu; jax_common.dll imports
  libpython3.14.dll, libstdc++-6.dll, libgcc_s_seh-1.dll, libwinpthread-1.dll.

Full build from scratch: about 4 h on the 4-core win11 host (~18k actions,
incl. LLVM/MLIR for the target and partly again for build tools).

## Pinned sources
- jax / jaxlib 0.11.2 (tag `jax-v0.11.2`)
- XLA 91888df6ce85102c30220e41d952065925e10886 (from jax's MODULE.bazel)
- rules_ml_toolchain c0eb2743b7b12b2bbcf0e1888e26d36ba6b093de (pywrap rules)
- LLVM/MLIR, StableHLO, Shardy, abseil, protobuf, grpc, ... : whatever the
  above pin; Bazel downloads them (repository cache).
- Bazel 8.7.0 (official windows-x86_64 binary; needs msvcp140/vcruntime140
  DLLs, taken from the PyPI msvc-runtime wheel and put next to bazel.exe).

## Design

### C/C++ toolchain (build/mingw/, from the recipe's BUILD.bazel.in and
cc_toolchain_config.bzl)
- MSYS2 clang with the GNU driver (x86_64-w64-windows-gnu), libstdc++,
  `-fuse-ld=lld`. `compiler = "clang"` so `@rules_cc//cc/compiler:compiler`
  is "clang" on `@platforms//os:windows`: LLVM's Bazel overlay already has
  an `is_windows_clang_mingw` config for exactly that (Support linkopts,
  native target triple, forward slashes), and abseil/protobuf/grpc select
  their GCC/clang flags. Selects on `@platforms//os:windows` alone still
  pick Windows sources (correct for MinGW) and sometimes MSVC flags (patched
  where hit).
- Registered with `--extra_toolchains` and toolchain resolution
  (`--config=clang_local` then re-enabling
  `--incompatible_enable_cc_toolchain_resolution`, as the earlier probe).
  `--noenable_platform_specific_config` drops jax's `common:windows` MSVC
  options (/Zc:preprocessor, /std:c++17, /DEBUG, ...).
- Legacy Bazel features do the bulk (include paths, -c/-o, whole-archive,
  param files); the config adds:
  - artifact names: .exe, .dll, and interface libraries `*.if.lib`
    (cc_import only accepts .ifso/.tbd/.lib/.so/.dylib as interface
    libraries; lld reads a GNU import library under any name).
  - `targets_windows` (Windows DLL/def-file logic in cc_binary),
    `supports_interface_shared_libraries` with
    `-Wl,--out-implib,%{interface_library_output_path}`, and the .def file
    passed as a plain input (lld's MinGW driver accepts it). This is what the
    pywrap rules need: jax_common.dll + its import library, the .pyd files
    link against it (the probe's "interface_library ... produces no .lib"
    error).
  - own action_configs for the DLL link actions: the legacy ones run
    link_dynamic_library.sh (ELF .ifso builder) whenever interface libraries
    are supported, which cannot run on Windows.
  - an empty `runtime_library_search_directories` feature (no -rpath).
  - flags: `-std=gnu++17` (strict c++17 hides M_PI etc. in MinGW headers),
    `-D_USE_MATH_DEFINES -DWIN32_LEAN_AND_MEAN -DNOGDI
    -D_WIN32_WINNT=0x0A00`, `-DNOMINMAX` for C++ only (C code uses the
    min/max macros of MinGW's stdlib.h), `-O2 -ffunction-sections
    -fdata-sections`, `-Wl,--gc-sections -s`; `-mavx` like upstream wheels.
- Fixed action PATH (`--action_env/--host_action_env=PATH=...`): it is part
  of every action key, so the dev builds and the final makepkg build share
  the cache; it also has bazel/ (MSVC runtime for Bazel's launcher tools).

### Runtime DLLs of build tools
Build tools (filewrapper, tblgen, protoc, ...) are executables linked
against libstdc++-6.dll etc. like everything else (dynamic, as usual for
MSYS2). Many Starlark actions run them without any PATH, so the loader
would not find the DLLs (0xC0000135). `@mingw_prefix//:runtime_dlls`
(cc_import of libstdc++-6.dll, libgcc_s_seh-1.dll, libwinpthread-1.dll) is
added to every executable via `--@rules_cc//:link_extra_libs` and
`--@bazel_tools//tools/cpp:link_extra_libs`; the
`copy_dynamic_libraries_to_binary` feature then puts the DLLs next to each
.exe. MSVC-built tools (Bazel's def_parser, the py_binary launcher) need
the VC runtime, which is only on the action PATH; the two pywrap def-file
actions and the wheel action are patched to `use_default_shell_env`.

### Windows system libraries
MSVC-oriented BUILD files add system libraries with `#pragma comment(lib)`
or `-DEFAULTLIB:x.lib` / `-defaultlib:x.lib` linkopts; clang ignores the
pragma for MinGW targets and treats the linkopts as harmless -D/unused
flags. The toolchain's default link flags therefore list the usual ones
(ws2_32 shlwapi dbghelp bcrypt crypt32 normaliz ole32 uuid psapi iphlpapi
ntdll version); lld only adds an import when a symbol is used.

### Python
- Extensions are built for MSYS2's Python: a `py_cc_toolchain`
  (`//build/mingw:py_cc_toolchain`) gives the headers of
  `${MINGW_PREFIX}/include/python3.X` (new_local_repository `mingw_prefix`
  = the MSYS2 prefix, in MODULE.bazel) and links `-lpython3.X`.
- Build tools (py_binary: wheel builder, def-file filter, ...) still run on
  rules_python's hermetic CPython (MSVC build); only the C API side differs.
- The .pyi stubs are not built on Windows: stubgen imports the freshly built
  extensions with the build-tool Python, which is not the Python they are
  for. They are optional.

### pywrap / DLL layout
Unchanged from upstream Windows: `jaxlib/jax_common.dll` holds everything
(XLA, MLIR, ...) and exports only `Wrapped_PyInit_*` (jax_common.json filter
-> .def); each `*.pyd` is a thin wrapper importing from it.

## Recipe files
- BUILD.bazel.in, cc_toolchain_config.bzl, mingw_prefix.BUILD: installed
  into the jax tree as build/mingw/ by prepare() (@MINGW_PREFIX@, @PYVER@
  substituted).
- build() writes .bazelrc.user (`common:mingw` config, read by jax's
  .bazelrc try-import) every time, so `makepkg -e` uses the same options;
  XLA and rules_ml_toolchain come from the patched source trees via
  `--override_module`.
- build() retags the wheel (the wheel builder runs on the hermetic Python,
  which calls it win_amd64) to cp3X-cp3X-mingw_x86_64_ucrt_gnu.

## Patches
0xxx apply to jax, 1xxx to XLA, 2xxx to rules_ml_toolchain (prepare()).
- 0001-jax-MinGW-build-integration: MODULE.bazel gets the `mingw_prefix`
  repository and single_version_override patches for the BCR modules curl
  (/D copts -> -D; -l system libs for windows_gnu) and boringssl
  (`windows_gnu` config: -std=c11 instead of /std:c11, no -utf-8), both in
  third_party/mingw/; the jaxlib wheel action uses the default shell env
  (VC runtime of the py_binary launcher); no .pyi stubs on Windows
  (jaxlib/tools/BUILD.bazel, build_wheel.py): stubgen would import the
  MinGW extensions with the MSVC build-tool Python.
- 0002-jax-cpu_feature_guard-MinGW-uses-GCC-cpuid: __cpuidex/_xgetbv path
  only for _MSC_VER; MinGW uses the GCC inline assembly.
- 1001-xla-eigen-MinGW-AVX-Packet2d: Eigen patch (via tf_http_archive
  patch_file): with clang's __GXX_ABI_VERSION 1002 Eigen wraps Packet2d on
  MinGW+AVX, so the AVX-without-AVX2 psin/pcos/ptan<Packet4d> must call
  p*<Packet2d> explicitly (otherwise "no matching function for call to
  'sin'").
- 1002-xla-slinky-MinGW-aligned-malloc: slinky uses _aligned_malloc for
  _WIN32, not only _MSC_VER (no posix_memalign on MinGW).
- 1003-xla-GNU-style-D-flags-on-Windows: farmhash and profiler copts
  /DFOO -> -DFOO (accepted by cl/clang-cl as well).
- 1004-xla-filewrapper-write-in-binary-mode: filewrapper truncates its
  output at a tellp() offset; in text mode the CRs made it cut the end off
  the generated .cc (embed_gpu_specs.cc: "expected '}'").
- 1005-xla-tsl-random_device-default-token-on-Windows: tsl::random used
  std::random_device("/dev/urandom"); MinGW's libstdc++ throws
  "unsupported token" (first jnp op failed), MSVC ignores the token.
- 2001-rules_ml_toolchain-pywrap-def-file-actions-use-shell-env:
  WinDefFileParse/WinDefFileFilter actions get PATH (VC runtime for
  def_parser.exe and the py_binary launcher).

## Work locations (win11)
- Recipe/build dir: ~/jaxpkgs/mingw-w64-python-jaxlib (makepkg `src/` is the
  development tree; the src trees are git repos, `git diff` = new changes).
- Dev build script: ~/jaxpkgs/jb.sh (same bazel flags as build(), with
  `--output_user_root=E:/bzl_jax`); logs ~/jaxpkgs/b*.log;
  ~/jaxpkgs/errs.sh summarizes errors of a log.
- Bazel output root E:/bzl_jax (output base gdkdqwog for the src tree;
  repository cache E:/bzl_jax/cache/repos). Re-running the package build
  must use `JAXLIB_BAZEL_ROOT=E:/bzl_jax makepkg-mingw -e` to reuse it
  (the action keys include the fixed action PATH, i.e. the srcdir path).
  E:/bzl_jax/43ldfxgn and ags6bw53 are the old probe output bases (stale).
- ~/jaxpkgs/mkseries.sh regenerates the patch series from the pristine
  tarballs and the src trees; ~/jaxpkgs/wt.sh / wtest: ad-hoc wheel tests.
- jax (pure Python) is the separate recipe mingw-w64-python-jax, built in
  ~/jaxpkgs/mingw-w64-python-jax.

## Gotchas
- BUILD files that XLA's repository rules copy in (tf_http_archive
  build_file, e.g. third_party/farmhash/farmhash.BUILD) are copies on
  Windows (no symlinks): after changing one, delete
  `E:/bzl_jax/gdkdqwog/external/@<repo>.marker` to force a refetch.
- Bazel's own patcher (single_version_override) needs git-style diffs
  (`diff --git` headers) for multi-file patches.
- To stop a running build, kill the Bazel server with `taskkill /T` (tree)
  by PID, else orphaned clang processes keep output files open.

## Open items
- No .pyi stubs in the wheel (see 0001).
- GPU plugins/CUDA are not built (CPU only, like the request).
- jaxlib's own test suite was not run; verification is the check() and the
  script described under Status.
