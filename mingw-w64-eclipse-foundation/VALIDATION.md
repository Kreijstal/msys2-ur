# UCRT64 validation — 2026-10-16

The release contains 163 new packages from 29 recipes: 143 runtime packages
and 20 additional build/check dependencies. All selected archives match the
PKGBUILD hashes recorded in their `.BUILDINFO`. All 56 source inputs were
verified against the recipe SHA-256 checksums and are included in the source
archive on the existing `x11-shared-20260731` release.

## Focused rebuilds

- Foundation install target: `makepkg --cleanbuild --force --noconfirm`
  passed, including `bash -n eclipse-foundation`.
- JSVG: `SRCDEST=$HOME/eclboot/srcdest makepkg --noextract --force --noconfirm`
  passed its SVG rendering and class-load checks. Version `2.1.0-2` includes
  the Aries SPI Fly runtime dependency missing from the earlier binary.
- Existing platform-core build log records `OK (120 tests)`; LSP4J records
  `OK (175 tests)`. The recipes also exercise class loading, OSGi resolution
  and native SWT controls.

## Clean installation and workbench

A local mirror of the release packages was installed into an empty pacman
root on Windows 11, using an isolated database and the official UCRT64
repository for libwinpthread:

```sh
pacman --config "$task/clean-pacman.conf" --root "$root" \
  --dbpath "$root/var/lib/pacman" --cachedir "$task/payloads" \
  -S --noconfirm mingw-w64-ucrt-x86_64-eclipse-foundation
pacman --config "$task/clean-pacman.conf" --root "$root" \
  --dbpath "$root/var/lib/pacman" -Qkk
```

Both commands returned 0. Pacman installed 145 packages, including the
previously released source-built OpenJDK 28 and official libwinpthread.
Every installed package reported zero altered files.

The test then removed the original UCRT64 prefix from PATH, retaining only
the new prefix, MSYS shell tools and Windows system directories. It compiled
and installed a small startup test bundle using the new root's javac, then
ran its launcher with state/workspace paths containing spaces and fresh
Java home/temp directories. The workbench started and closed cleanly; the
final console log was empty. The report recorded:

```text
workbench windows: 1, workbench running: true
visible=true perspective=org.eclipse.ui.resourcePerspective
bundles: 139 active/starting 85 resolved 54 other 0
SWT 4974 win32, java 28
```

The bundle count includes the startup test bundle. Runtime-only installation
has fewer bundles than the development prefix, which also contains check
and build dependencies. The capture composes SWT control renderings for
headless Windows sessions; it is not a desktop screenshot.

The source release includes the test harness, test bundle source, package
inventory, build logs and installation evidence. This validates the
foundation workbench and libraries; the full Java IDE and PDE tooling are
outside this package's scope.
