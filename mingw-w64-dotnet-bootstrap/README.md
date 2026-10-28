# Source-built .NET packages

This recipe runs the source bootstrap from the trusted MSYS2 UCRT64 Mono
6.12 seed. It builds CoreCLR with CLANG64, then builds SDK stage 2 with the
source-built stage-1 SDK. It does not import an existing SDK installation,
Microsoft binary NuGet packages, or runtime/SDK downloads.

All split packages use bundle version **8.0.131**. The runtime sources are
**8.0.0**; the SDK's framework/pack directory aliases retain **8.0.31** as in
the bootstrap. These version aliases do not imply the later servicing fixes.
Targeting metadata records the actual built runtime file versions: **8.0.0.0**
for implementations, while pure forwarding shims retain their generated
versions. It must not use the 8.0.31 directory alias: that would make MSBuild
discard independently serviced package assemblies as if the framework already
contained those fixes. The reference-pack generator distinguishes
implementations from forwarding shims. Packaging also reads every actual runtime PE file version, including
when repackaging cached source-built outputs.

This is the experimental bootstrap's SDK, including its documented shims and
unsupported components, rather than a complete upstream Windows SDK.

| CLANG64 package suffix | Installed files |
| --- | --- |
| `dotnet-host` | `bin/dotnet.exe` launcher, `lib/dotnet/dotnet.exe`, hostfxr |
| `dotnet-runtime` | CoreCLR shared framework under `lib/dotnet/shared` |
| `dotnet-targeting-pack` | .NET 8 reference assemblies and generators |
| `dotnet-sdk` | Self-hosted SDK, templates, local library feed, host/runtime packs |
| `dotnet-bootstrap-tools` | Roslyn generations, Mono-hosted MSBuild/NuGet, net472 dependencies; `csc-bootstrap` and `msbuild-bootstrap` launchers |
| `dotnet-runtime-mono` | Separate Mono shared framework under `lib/dotnet-mono`; `dotnet-mono` launcher |
| `dotnet-crossgen2` | ReadyToRun compiler and `crossgen2` launcher |
| `dotnet-ilasm` | CoreCLR IL assembler, `bin/ilasm-dotnet.exe` |
| `dotnet-host-devel` | `include/dotnet` headers; hosting DLLs/import/static libraries in `lib/dotnet/hosting` |
| `dotnet-mono-devel` | Mono embedding headers/libraries and mono-sgen under `lib/dotnet-mono/embedding` |

`dotnet-host` also installs a CLANG64 shell profile setting `DOTNET_ROOT`
and `DOTNET_ROOT_X64` when unset, so generated native apphosts can locate the
runtime. Open a new CLANG64 shell after installation or source
`/clang64/etc/profile.d/dotnet.sh`. For Windows shells, set these variables
to the Windows path of `clang64/lib/dotnet` when running an apphost directly.

The full package prefix is `mingw-w64-clang-x86_64-`. The bootstrap tools
still need the UCRT64 Mono seed at runtime. Mono embedding files live in a
private directory so they can coexist with that seed.

## Build

The bootstrap sources are https://github.com/Kreijstal/dotnet-mingw-bootstrap.
The recipe pins tag `msys2/dotnet-bootstrap-8.0.131-2` (commit 2e8208f): the
earlier 3cbf210 plus the packaging changes this recipe used to carry as
patches, and the native launcher shared with cppcli (`packaging/`). Source
changes belong in that repository, not in patches here.

From a **CLANG64** shell, build normally:

```bash
makepkg-mingw -s
```

All source archives, including the pinned bootstrap commit, are declared
with checksums.
The recipe places them in a private build cache and rejects missing inputs
instead of fetching additional archives inside `build()`. Source trees have
upstream binary test resources removed before compilation. IL assembler
construction is included before stage 2 needs it.

The packaging commit also limits the preview bridge compiler's smoke tests
to its stable language version (C# 13), and extracts HostModel's shared
CoreCLR compiler sources along with the managed runtime tree. The final
Roslyn 5 compiler still runs the C# 14 tests. Native source commit detection
handles an early-closing tar-header reader, and the VB compiler prefix is
refreshed with the source-built dependencies it was compiled against. The
project-item reader preserves the shell's logical project path through the
short build junction.

The build needs substantial disk space and time. `DOTNET_BUILD_JOBS`
(default 4) controls native build concurrency. Logs and intermediate results
remain in `src/m612`. The recipe creates a short private Windows junction
under `/tmp/dnb.*` and records it in `src/.m612-root`, so the legacy Mono
compiler can read long source filenames. The junction points to the same
private source/build tree; it does not import another installation. Keep it
while reusing that build tree. After removing the build tree, remove its
junction with Windows `rmdir` (without `/s`), then remove the empty temporary
parent directory. A development retry may use
`DOTNET_BOOTSTRAP_START=N makepkg --noextract --force` to resume this
recipe's own build tree after fixing a failure; normal builds start at step 1.
No existing bootstrap outputs are copied into a clean build. Stage 3/4 determinism rebuilds are not needed to install stage 2 and
are not repeated by the package recipe.

`check()` builds and runs an offline console application from a staged
installation whose path contains spaces, through both the dotnet launcher
and its generated native apphost. The same application runs on the packaged
Mono runtime too. It also checks SDK discovery,
crossgen2, ilasm, and the native launcher's Unicode paths, argument quoting,
pipes, current directory and exit status. It compiles native consumers of
nethost and the Mono embedding API and builds a C# 12/resource project with
the relocated Mono-hosted bootstrap tools. The bootstrap itself runs its
runtime, SDK, generator, publishing and interop checks along the way.

Install the resulting split packages with `pacman -U`. For example, to
install all outputs from this build:

```bash
pacman -U mingw-w64-clang-x86_64-dotnet-*.pkg.tar.zst
```

Build the [C++/CLI package](../mingw-w64-cppcli/README.md) afterwards.
[Portable.NET](../mingw-w64-pnet-bootstrap/README.md) is an independently
packaged C-only bootstrap root; it is not the seed of this SDK recipe.

The SDK package forwards its two bootstrap NetAnalyzers import stubs to the
optional `dotnet-sdk-netanalyzers` provider. The provider owns the real analyzer
assemblies, generated configuration and imports; the SDK retains ownership of
its forwarding files. Non-placeholder upstream imports are preserved. Updating
these package-only imports does not rebuild or replace compiler/runtime binaries.
