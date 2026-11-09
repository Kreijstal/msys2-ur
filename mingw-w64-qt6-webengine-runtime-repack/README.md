# Qt WebEngine 6.11.2 runtime packaging maintenance

This recipe produces `qt6-webengine` **6.11.2-3** for CLANG64 and UCRT64 from
the SHA256-pinned published 6.11.2-2 packages. It is a packaging-only rebuild;
it does not compile Qt or Chromium. All existing runtime files, headers,
resources, dependencies and licenses remain unchanged. Nine `.debug` companions
per environment are excluded. Recipe options disable stripping and new debug
symbol generation, so makepkg cannot reintroduce these companions.

Each package includes the original `.BUILDINFO`, `.PKGINFO` and a repack
provenance receipt under `share/doc/qt6-webengine/runtime-repack/`. The new
`.BUILDINFO` describes the packaging host and hashes this maintenance recipe;
it must not be interpreted as the original Qt compiler environment.

In an MSYS2 CLANG64 or UCRT64 shell:

```sh
makepkg --cleanbuild --force --noconfirm
```

The packaging operation also works on Linux with Python, zstd and makepkg,
using `MINGW_PACKAGE_PREFIX=mingw-w64-clang-x86_64` or
`mingw-w64-ucrt-x86_64`. `--nodeps` is appropriate there because the Windows
runtime dependencies cannot be installed into the Linux build host; the
packaging operation does not execute Windows binaries.

The independent [artifact audit](../tests/qt6-webengine-runtime-repack/audit-package.py)
compares every retained file's bytes and mode, dependency/license metadata,
the removed symbol list, the regenerated package version/mtree, and the
retained original provenance. The [release record](../tests/qt6-webengine-runtime-repack/release-20261109.json)
records the build, installation and publication results.
