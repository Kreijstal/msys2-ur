# Butterscotch for MSYS2 UCRT64 and CLANG64

Native Windows runner for compatible GameMaker: Studio game data. The source
snapshot is pinned to `f3db244910b4ddf20596dd918cc2bbd061745957` (2026-10-15).

Build in a UCRT64 shell:

```sh
pacman -S --needed mingw-w64-ucrt-x86_64-{gcc,cmake,ninja,pkgconf,SDL2,ffmpeg}
makepkg --cleanbuild --syncdeps --noconfirm
pacman -U mingw-w64-ucrt-x86_64-butterscotch-*.pkg.tar.zst
```

Alternatively, build in a CLANG64 shell:

```sh
pacman -S --needed mingw-w64-clang-x86_64-{clang,cmake,ninja,pkgconf,SDL2,ffmpeg}
makepkg --cleanbuild --syncdeps --noconfirm
pacman -U mingw-w64-clang-x86_64-butterscotch-*.pkg.tar.zst
```

Run from the corresponding MSYS2 shell:

```sh
butterscotch --help
butterscotch /path/to/game/data.win
```

The package enables SDL2, both OpenGL renderers, miniaudio, FFmpeg video and
Box2D physics. Upstream's vendored libraries are compiled from the pinned
source snapshot. No game data is installed. Supply a compatible game's data;
YYC/GMRT builds are not supported by the upstream runner.

`makepkg` checks that the executable's help command starts successfully.
Game execution and installed dependency checks are recorded in `VALIDATION.md`
after the Windows build is tested.
