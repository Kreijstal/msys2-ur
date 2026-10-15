# Windows validation, 2026-10-16

## CLANG64

Package: `mingw-w64-clang-x86_64-butterscotch-0.r20261015.gf3db244-1`.
Upstream commit: `f3db244910b4ddf20596dd918cc2bbd061745957`.

Built natively on Windows 11 with Clang 23.1.3, CMake 4.4.4, SDL2 2.32.10
and FFmpeg 9.0.2, using:

```sh
MAKEFLAGS=-j4 CMAKE_BUILD_PARALLEL_LEVEL=4 makepkg --cleanbuild --force --noconfirm
pacman -U --noconfirm mingw-w64-clang-x86_64-butterscotch-0.r20261015.gf3db244-1-any.pkg.tar.zst
pacman -Qkk mingw-w64-clang-x86_64-butterscotch
```

Results: clean build and `check()` passed, installation passed, 27 package files
checked with zero altered files. FFmpeg was detected and linked. The installed
executable contains no build-directory paths. Its `.BUILDINFO` recipe hash
matches the PKGBUILD in the original CLANG64 build-source bundle (recipe
repository commit `cf4d3bdadb60e5f07d5034d7dcd3df8dbc339b16`).

`validate-dlls.py` recursively checked imports from the executable and all
third-party libraries, then loaded each library through the Windows loader:
97 third-party DLLs resolved and loaded. Windows system DLLs and virtual API
sets were handled separately. A plain recursive `ntldd` scan reports unresolved
optional Windows internals and API sets, so its unfiltered output was not used
as a pass/fail criterion.

The installed executable's `--help` also passed with `PATH` restricted to
`/clang64/bin` and Windows System32.

Three small test games from the pinned upstream source were run using the
installed executable, `--headless --exit-at-frame 1 --disable-log-colours`,
with an explicit save directory. Every process exited successfully, reached
frame 1, and emitted its expected output in order:

| Upstream test | Checked behavior |
| --- | --- |
| `object-index-iteration-test` | Collision callbacks: wall 2, wall 1, wall 3 |
| `simple-structs-methods-and-dynamic-methods` | Structs, method calls, dynamic methods and expected field values |
| `stack-unwinding` | Loop unwinds with final count 2047 |

The collision test also used `--screenshot-at-frame 1 --screenshot collision.png`.
The 1024 by 768 PNG passed CRC and decompression checks and was visually
inspected: the test's colored objects were rendered.

The SSH session exposes an old system OpenGL driver. These game tests used the
already installed CLANG64 Mesa package with `SDL_OPENGL_LIBRARY` pointing to
`/clang64/bin/opengl32.dll`, `GALLIUM_DRIVER=llvmpipe` and
`LIBGL_ALWAYS_SOFTWARE=1`. Mesa is a test dependency; users with suitable GPU
drivers can use the runner's normal SDL2/OpenGL path. Upstream `--headless`
still creates a hidden OpenGL window.

No commercial game, audio playback, video playback, controller input or
interactive desktop session was tested. The tested rendering path uses Mesa
software OpenGL.

The published build-source bundle includes the exact recipe, upstream source
archive, build log, test scripts, test output and screenshot.

## UCRT64

Package: `mingw-w64-ucrt-x86_64-butterscotch-0.r20261015.gf3db244-1`.
Same pinned upstream commit, built natively on Windows 11 with GCC 16.2.0,
CMake 4.4.4, SDL2 2.32.10 and FFmpeg 9.0.2. No upstream source patches were
needed. This variant depends on UCRT64 SDL2, FFmpeg and `gcc-libs`.

```sh
MAKEFLAGS=-j4 CMAKE_BUILD_PARALLEL_LEVEL=4 makepkg --cleanbuild --force --noconfirm
pacman -U --noconfirm mingw-w64-ucrt-x86_64-butterscotch-0.r20261015.gf3db244-1-any.pkg.tar.zst
pacman -Qkk mingw-w64-ucrt-x86_64-butterscotch
```

Results: build, `check()`, installation and package integrity checks passed
(27 files, zero altered). The binary's `.BUILDINFO` matches the current
PKGBUILD, and no build-host paths remain in the executable.

The same three upstream game tests listed above passed against the installed
UCRT64 executable with the same expected output and frame-1 exit. The
1024 by 768 screenshot passed PNG CRC and decompression checks. Help and
game tests used a PATH restricted to UCRT64 and Windows System32. Game tests
used UCRT64 Mesa software OpenGL with the same environment settings described
above, pointing to `/ucrt64/bin/opengl32.dll`.

The dependency checker used UCRT64 `objdump` to inspect imports and the Windows
loader to check DLL loading: 98 third-party DLLs resolved and loaded, with no
unresolved third-party imports. The UCRT64 source bundle includes the exact
recipe, source archive, build and installation logs, test scripts, test output
and screenshot. The untested features listed for CLANG64 also apply here.
