# Windows CLANG64 validation, 2026-10-16

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
matches this PKGBUILD.

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
