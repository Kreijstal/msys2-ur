# PaddlePaddle on MSYS2 MinGW (ucrt64) — porting notes

## Status

Working. `makepkg-mingw` of this recipe builds the package (about 1 h 45 min
on the 4-core win11 host, incl. bundled third-party deps) and its check()
passes; the package is installed on win11 (3.5.0.dev20260929-2).
- `import paddle; paddle.utils.run_check()`: "PaddlePaddle works well on 1 CPU"
- dygraph nn.Linear regression with SGD converges (loss 8.69 -> 2.6e-8)
- LAPACK ops through OpenBLAS (inv, eigvalsh), a static-graph program through
  the PIR executor, `paddle.jit.to_static(full_graph=True)`
- PaddleOCR 3.7.0 (PP-OCRv5 mobile det + en rec) reads all 9 cells of a
  generated table image; img2table's PaddleOCR backend extracts the 3x3 table.
- libpaddle.pyd links libpython3.14.dll; wheel tag cp314-cp314-mingw_x86_64_ucrt_gnu.

Fixed in -2 (patch 0008): run_check() aborted intermittently with
`terminate called after throwing std::out_of_range (unordered_map::at)` from
an exiting worker thread (14 of 280 runs under heavy CPU load with -1, 0 of
200 with -2). See "Thread-exit abort (fixed, patch 0008)" below.

Related packages (msys2-ur, built and installed on win11): python-crc32c,
python-bce-python-sdk, python-aistudio-sdk (wheel only upstream),
python-modelscope-hub, python-modelscope, python-bidi (maturin, pyo3 0.29.3 +
PYO3_CONFIG_FILE with lib_name=libpython3.14), python-paddlex (patch: relax
numpy<2.4 / PyYAML==6.0.2 / opencv-contrib-python==4.10 pins, detect cv2
without opencv-contrib-python metadata), python-paddleocr; python-img2table
2.0.0-2 (paddle extra no longer limited to python<3.14, makepkg -R).

## Pinned source
- Paddle `develop` @ 4793e33e12bc8b7a20f0750b3a79b4b6e68ea98d (2026-09-29),
  pkgver 3.5.0.dev20260929 (cp314 wheel, tag cp314-cp314-mingw_x86_64_ucrt_gnu)
- Submodules used by the CPU build: protobuf (v21.12), pocketfft, gflags,
  dlpack, utf8proc, warpctc, warprnnt, xxhash, pybind, threadpool, zlib, glog,
  eigen3, cryptopp(+cryptopp-cmake), nlohmann_json, yaml-cpp, libuv.

## Configure options
WITH_GPU=OFF WITH_MKL=OFF WITH_ONEDNN=OFF WITH_SYSTEM_BLAS=ON (system OpenBLAS,
also LAPACK at runtime) WITH_DISTRIBUTE=OFF WITH_TESTING=OFF WITH_XBYAK=OFF
WITH_SLEEF=OFF WITH_CINN=OFF ON_INFER=OFF WITH_SHARED_IR=OFF WITH_AVX=ON
PADDLE_SKIP_SUBMODULE_UPDATE=ON (new option). Environment: PADDLE_VERSION
(otherwise the git hash ends up in a global -D define and every commit
rebuilds everything), SKIP_STUB_GEN=1 (pybind11-stubgen is not packaged).

WITH_SHARED_IR=OFF matches upstream's Windows CI (ON_INFER=ON forces static
pir there): with a shared pir.dll the pass-registration macros put IR_API
(dllimport) on definitions outside pir.

## Design
- Upstream Windows DLL layout and export model are kept (common.dll, phi.dll,
  libpaddle.pyd; PADDLE_DLL_EXPORT is defined globally, so PADDLE_API is
  dllexport everywhere). CMAKE_SHARED_LIBRARY_PREFIX="" keeps the names.
- Linking uses lld: Paddle declares some data dllimport inside the defining
  DLL (COMMON_IMPORT_FLAG; MSVC resolves this with warning LNK4217, GNU ld
  cannot). lld also links the 115 MB phi.dll / 196 MB libpaddle quickly.
- GCC does not reproduce MSVC's export set: dllexport on an explicit
  instantiation of an already-instantiated class template is ignored, and
  vtables are only emitted with the key function. common.dll and phi.dll
  therefore export all global symbols of their *own* objects via a generated
  .def (tools/mingw_gen_def.py, ~45k symbols for phi, PE limit 65535).
  Static archives linked into them (protobuf, glog, framework_proto, ...) are
  not exported: libpaddle links its own copies, as with MSVC, and exporting
  them makes lld report duplicates (import symbol vs. later archive member).
  COMDAT symbols of third-party namespaces (std, Eigen, google, ...) are
  filtered out too.
- Kernels: GCC needs the explicit instantiations of the non-Windows
  PD_REGISTER_* macros; the MSVC-only exported instantiations become
  dllexport explicit instantiation *declarations* on MinGW.
- TypeRegistry<Base> is explicitly instantiated once in phi; previously each
  DLL had its own registry from the header and type ids collided
  (TypeInfoTraits<TensorBase, VariableCompatTensor>::classof() returned true
  for DenseTensor -> crash in Tensor.dtype on nn.Linear creation).
- Bundled third-party code stays bundled: Paddle's external projects have no
  system-library switches, glog is patched by Paddle, protobuf is pinned to
  21.12 and linked statically into each DLL (as upstream on Windows). Only
  BLAS/LAPACK come from the system (OpenBLAS).

## Patches (recipe dir, git format-patch on top of the pinned commit)
1. 0001 cmake: MinGW-w64 toolchain and third-party support (GNU flag paths,
   gnu++20, -Wa,-mbig-obj, no lib prefix, lld, MinGW names of bundled libs,
   warpctc MSVC flags via patches/warpctc/CMakeLists.txt.mingw.patch,
   pocketfft aligned_alloc, LAPACK from OpenBLAS, dirent MSVC-only,
   PADDLE_SKIP_SUBMODULE_UPDATE, FindPythonLibs instead of the .lib hack)
2. 0002 cmake: mkdir races in execute_process pipelines (all COMMANDs of one
   execute_process run concurrently)
3. 0003 cmake: DLL exports via .def from own objects, dbghelp/ws2_32,
   libpaddle import lib without dumpbin, no openblas.dll copy
4. 0004 MSVC-only code paths: __declspec(align) (silently dropped by GCC!),
   cpuid.h, gettimeofday/sleep/pid_t shims, dirent d_type, wstring fstream,
   wchar_t* in error messages, dynload DLL names, float16.h `#define
   __SSE2__` (empty -> breaks gcc 16 <bits/version.h>), <cstdint>
5. 0005 phi: kernel instantiation export model + single TypeRegistry
6. 0006 sot: py3.14 PyFrame_GET_CODE raw .bits workaround MSVC-only
7. 0007 python: wheel packaging (import libs, lib names, system OpenBLAS,
   opt_einsum>=3.3.0)
8. 0008 phi: ThreadDataRegistry uses std::mutex instead of std::shared_mutex
   on MinGW (winpthreads rwlock static-init race, see below)

## Work layout (for resuming)
- Local git tree: /home/kreijstal/.claude/jobs/b482be90/tmp/paddle, branch
  `mingw` (granular history) and `series` (the 7 topic commits = patches).
- win11: ~/paddlepkgs/src/Paddle (rsync -aL of the local tree incl. .git;
  never --delete: configure writes generated sources into the src tree),
  ~/paddlepkgs/build (ninja; dev tree, PADDLE_VERSION pinned to a git
  version, so it cannot produce the package), ~/paddlepkgs/configure.sh, build.sh (pins
  PADDLE_VERSION=3.5.0.dev20261006+a5e0abd41af to match existing objects),
  smoke.py (the success test), ~/paddlepkgs/mingw-w64-python-paddlepaddle
  (makepkg dir; its src/build-UCRT64 is the package build tree, rebuilt
  incrementally with `makepkg -e` after applying a new patch to src/Paddle by
  hand), mk.sh (makepkg wrapper -> mk.log/mk.done).
- Repro scripts: stressload.sh N (8 busy-loop pythons + N runs of
  /tmp/chk.py, results in stress.out), thload.sh/thstress.sh (same with
  /tmp/chk2.py, which loads /tmp/termhook.dll: a std::set_terminate backtrace
  handler plus IAT hooks that log failing pthread_rwlock_* calls).
- Full dev build: ~75 min for 2000 edges at -j4 (phi kernels dominate).

## Known warnings / noise
- configure runs `pip install pyyaml/jinja2/pybind11-stubgen`; under PEP 668
  these fail harmlessly.
- lld prints "locally defined symbol imported ... [LNK4217]" warnings (the
  behaviour lld is used for).
- importing paddle prints setuptools' "_get_vc_env is private" warning.
- importing paddleocr/paddlex pulls modelscope -> peft -> transformers ->
  sentencepiece; the repo's python-sentencepiece 0.2.1-1 is broken on win11
  (0xc0000139, needs a rebuild against current gcc-libs) - the import error is
  handled, only the faulthandler dump from the stray sitecustomize shows.

## Thread-exit abort (fixed, patch 0008)
Symptom: `terminate called after throwing an instance of 'std::out_of_range'
what(): unordered_map::at` from a non-Python thread, right after the
static-graph part of run_check() (multi-threaded PIR interpreter), while the
main thread is already in the dygraph part.

Where: a terminate handler (std::set_terminate + RtlCaptureStackBackTrace,
symbols from `nm` of the unstripped phi.dll) showed the throw in
`phi::ThreadDataRegistry<paddle::memory::HostMemoryStatReserved0>::
ThreadDataHolder::~ThreadDataHolder()` (phi/common/thread_data_registry.h),
called from phi.dll's CRT TLS callback (DLL_THREAD_DETACH) of an interpreter
worker thread leaving through winpthreads/_endthreadex. The destructor's
UnregisterData() -> AccumulateToAnotherThread() does `tid_map_.at(tid)`; it
is a noexcept TLS destructor, so the exception terminates the process.

Why: the registry lock is a std::shared_mutex, which libstdc++ implements as
a pthread_rwlock_t with PTHREAD_RWLOCK_INITIALIZER. winpthreads initializes
such locks lazily and not thread-safely: pthread_rwlock_init() first stores
NULL into the lock, and rwlock_static_init() returns EINVAL when another
thread finished the init first; both make pthread_rwlock_wrlock() return
EINVAL to the thread racing the first locker. std::shared_mutex::lock() only
checks for EDEADLK, so that thread runs RegisterData() without the lock and
then "unlocks" a lock it never held, which also corrupts the rwlock counters.
The memory-stat registries are first used concurrently by the interpreter's
worker threads (CPUAllocator -> StatAllocator -> Stat<...>::Update), so the
unordered_map gets corrupted and a later lookup at thread exit fails.
Evidence: IAT hooks on phi.dll's pthread_rwlock_* imports logged
`wrlock ret=22` from Stat<HostMemoryStatReserved0/Allocated0>::Update in
most runs under load; a standalone test (4 threads first-locking a fresh
PTHREAD_RWLOCK_INITIALIZER rwlock) fails wrlock 395 times in 2000 rounds.
Not a pthread id reuse or TLS-order problem (checked separately).

Fix: on __MINGW32__ the registry uses std::mutex (winpthreads initializes
static mutexes with a CAS), as upstream already does on macOS. No other
std::shared_mutex is compiled in the CPU build (allocator_facade's
shared_timed_mutex members are CUDA/XPU/custom-device only; phi::RWLock uses
a plain mutex on _WIN32). The root bug is in winpthreads (rwl_ref /
rwlock_static_init) and libstdc++ ignoring the error; worth reporting
upstream. Any other MinGW code using a static-initialized std::shared_mutex
under concurrent first use is affected the same way.

## Open items
- Not ported/enabled: oneDNN, xbyak JIT kernels, sleef, distributed, CINN,
  custom device, inference library (ON_INFER).
- Process-wide singletons defined inline in headers (profiler
  HostEventRecorder, memory StatRegistry) are per-DLL like with MSVC; only
  affects profiling/memory statistics.
