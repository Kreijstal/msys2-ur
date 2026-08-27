# Packaging for MSYS2-UR

This document records the packaging, validation, publication, and repository
maintenance practices learned while building both MSYS-runtime packages and
native MinGW packages for MSYS2-UR.

It describes the desired process for new work. Existing recipes and the current
release contain historical exceptions; those exceptions are inventory and debt,
not templates to copy.

## 1. Understand the three separate layers

Do not treat every package associated with MSYS2-UR as the same kind of work.

### 1.1 The `msys2-ur` source repository

This repository primarily contains **MSYS-runtime PKGBUILDs**. These packages:

- run in the MSYS2 POSIX compatibility environment;
- normally install below `/usr`;
- are built from an **MSYS shell** with `makepkg`;
- commonly produce `x86_64` packages such as X11 libraries and X servers; and
- may link against `msys-2.0.dll` and use MSYS/Cygwin-flavoured build logic.

The normal local command is therefore:

```bash
makepkg -s
```

not `makepkg-mingw`.

### 1.2 The `MINGW-packages` source repository

Native Windows packages belong in an MSYS2 `MINGW-packages` checkout. These
packages:

- produce native PE executables and DLLs;
- install below `/mingw64`, `/ucrt64`, `/clang64`, `/mingw32`, or
  `/clangarm64`;
- use `${MINGW_PACKAGE_PREFIX}` in package and dependency names;
- use `${MINGW_PREFIX}` for installed paths; and
- are built with `makepkg-mingw` and an explicit `MINGW_ARCH`.

Examples include native GUI applications, MinGW libraries, Qt, and
OpenTerminal.

Do not put a native UCRT64 recipe into this repository merely because the
result will be published through MSYS2-UR. Develop it in the appropriate
`MINGW-packages` branch, then publish the resulting package archive to the
MSYS2-UR binary repository if desired.

### 1.3 The GitHub release as a binary pacman repository

The GitHub release is an aggregate distribution layer. It can contain:

- MSYS packages built from this repository;
- native MinGW packages built from `MINGW-packages`;
- `msys2ur.db` and `msys2ur.files`; and
- their `.tar.zst` compatibility names.

The release is not proof that every package has a recipe in this repository,
and a recipe in this repository is not proof that the package is present in
the release database.

The existing `x11-shared-20260731` release is a mixed historical aggregate. It
contains package archives not represented by the current source tree, omits
many current recipe outputs, and retains several obsolete package archives.
New releases should publish an explicit manifest and a database generated from
the exact intended package set.

## 2. Golden rules

1. **Choose the runtime first.** Decide whether the result is an MSYS package
   or a native MinGW package before writing the PKGBUILD.
2. **Build in the matching environment.** Do not build an MSYS recipe from a
   generic Linux shell or a native MinGW recipe with plain `makepkg`.
3. **Never hard-code a MinGW prefix.** Use `${MINGW_PACKAGE_PREFIX}` and
   `${MINGW_PREFIX}`.
4. **Pin inputs and verify them.** Immutable sources and prebuilt bundles need
   real checksums.
5. **Do not confuse build tools with runtime dependencies.** Wine may host
   Windows build tools or validate a native binary on Linux without belonging
   in the native Windows package.
6. **Validate produced artifacts, not just exit codes.** A successful build can
   silently produce only static libraries, the wrong CRT, or missing DLLs.
7. **Keep upstream and private repository concerns separate.** An upstream PR
   must not depend on a private MSYS2-UR release.
8. **Regenerate the repository database from the complete intended package
   set.** Never update it from only the newly added archive.
9. **A successful local build does not authorize a push, release edit, or
   upload.** Publishing is a separate, explicit action.
10. **Keep release notes terse.** For package additions, use a line such as
    `Added OpenTerminal package.`

## 3. Environments and prefixes

### 3.1 Native MinGW environments

| `MINGW_ARCH` | `MSYSTEM` | package prefix | install prefix | typical compiler/runtime |
|---|---|---|---|---|
| `mingw64` | `MINGW64` | `mingw-w64-x86_64` | `/mingw64` | GCC, MSVCRT |
| `ucrt64` | `UCRT64` | `mingw-w64-ucrt-x86_64` | `/ucrt64` | GCC, UCRT |
| `clang64` | `CLANG64` | `mingw-w64-clang-x86_64` | `/clang64` | Clang, UCRT |
| `mingw32` | `MINGW32` | `mingw-w64-i686` | `/mingw32` | 32-bit GCC |
| `clangarm64` | `CLANGARM64` | `mingw-w64-clang-aarch64` | `/clangarm64` | AArch64 Clang |

Both MINGW64 and UCRT64 compilers may report a target such as
`x86_64-w64-mingw32`. The target triplet alone does **not** identify the CRT.
Use the selected MSYS2 environment, compiler configuration, and PE imports to
confirm the result.

A UCRT-linked binary or runtime DLL normally imports `api-ms-win-crt-*` DLLs.
Do not label that payload MINGW64 merely because the compiler executable is
named `x86_64-w64-mingw32-g++`.

### 3.2 MSYS environment

MSYS-runtime recipes are built from the MSYS shell and normally install below
`/usr`. They use unprefixed dependencies such as `libx11`, `gcc`, and `meson`.
The current X11 recipes rely on the `CHOST` loaded from MSYS2's
`/etc/makepkg.conf`.

### 3.3 `arch=('any')` versus `mingw_arch`

In MINGW-packages, this common pairing is intentional:

```bash
arch=('any')
mingw_arch=('ucrt64' 'clang64')
```

`arch=('any')` is package metadata used by the shared PKGBUILD machinery. It
does not mean that a contained PE binary can run on every CPU. `mingw_arch`
controls which native MSYS2 environments build the recipe.

In this repository's MSYS recipes, use an accurate pacman architecture such as
`arch=('x86_64')` or `arch=('i686' 'x86_64')`. Do not copy `arch=('any')` from a
MINGW recipe without understanding the difference.

## 4. Find the real package identity

A recipe directory is not always the package name.

Before building or publishing, source or inspect the PKGBUILD and record:

- `pkgbase`;
- every value in `pkgname`;
- `pkgver` and `pkgrel`;
- `arch` and, for MINGW packages, `mingw_arch`;
- `provides`, `conflicts`, and `replaces`; and
- every runtime and build dependency.

Split packages produce more than one archive. Current examples include:

- `libtool` → `libtool` and `libltdl`;
- `xorg-server` → multiple server/common/devel/utility packages; and
- `xlibre-xserver` → the corresponding XLibre alternatives.

`xorg-server` and `xlibre-xserver` are alternatives. Their `provides` and
`conflicts` fields are deliberate; do not install or publish them as if they
were one combined stack.

Known source-tree caveats:

- `xorg-server-cygwin/` is legacy Cygport material, not a normal PKGBUILD
  directory.
- Both `librandr/` and `libxrandr/` currently declare `libxrandr`; the newer
  recipe with current shared-DLL logic should be treated as authoritative until
  the duplicate is removed.
- Some package names are derived from variables, so directory-name matching is
  insufficient.

A repository helper must derive package names from PKGBUILDs, not from folder
names.

## 5. Choose the package strategy

Use the first viable option in this order.

### 5.1 Conventional source package

Prefer a normal source package when the project can be built in an MSYS2
runner with dependencies available from configured repositories.

A conventional package should:

- download immutable, checksummed sources;
- apply small, reviewable patches in `prepare()`;
- use an out-of-tree build when supported;
- run meaningful tests in `check()`;
- install through `DESTDIR="${pkgdir}"`; and
- install the applicable license texts.

### 5.2 Producer/consumer package split

Use a producer package when a large or specialized build emits inputs consumed
by another package. This is preferable to copying an opaque cache by hand.

The consumer must depend on a normal, versioned package:

```bash
depends+=("${MINGW_PACKAGE_PREFIX}-example-thirdparty=${pkgver}")
```

The producer must publish a manifest of the exact headers, archives, objects,
or generated files that it supplies.

For stacked upstream work, land the producer/third-party branch first. Keep the
consumer branch stacked on that upstream branch. Do not rewrite either upstream
branch to fetch from MSYS2-UR.

A private branch used only to build the MSYS2-UR release may consume packages
from MSYS2-UR, but those private dependencies must not leak into the upstream
PR.

### 5.3 Binary repackaging

Binary repackaging is a last resort, not a shortcut around build work. It is
appropriate when the complete build genuinely requires tools unavailable on a
normal MSYS2 runner, provided that licensing permits redistribution and the
package is labelled honestly.

Requirements:

- pin the source snapshot represented by the binary;
- use a versioned, downloadable bundle for clean CI;
- checksum the outer archive;
- include a per-file manifest with relative paths and hashes;
- include build provenance and component revisions;
- verify architecture and CRT;
- preserve files that must remain colocated;
- use `options=('!strip' '!debug')` for a prebuilt PE payload when stripping or
  split-debug processing is unsafe;
- include all required license notices; and
- document why a source build is not yet represented by the PKGBUILD.

A bare local source entry such as this is not clean-clone buildable:

```bash
source=('locally-created-bundle.tar.zst')
```

It works only while that untracked file exists beside the PKGBUILD. Before the
recipe is pushed or treated as CI-ready, publish the bundle at an immutable URL
or implement the build in the recipe.

### 5.4 Runtime boundary rule

Package the runtime for the target platform, not every tool used to produce or
test it.

Example: OpenTerminal is a native Windows UCRT64 application. Its Linux build
and integration pipeline may use Wine, .NET Framework under Wine, and an
external OpenXaml compatibility runtime. None of those Linux compatibility
components belongs in the native Windows MSYS2 package. The native package
contains its PE executables, MinGW runtime DLLs, fonts, and XBF assets. Wine and
OpenXaml stay in separate Linux integration instructions.

## 6. Authoring an MSYS-runtime PKGBUILD

A minimal shape is:

```bash
pkgname=example
pkgver=1.2.3
pkgrel=1
pkgdesc='Example MSYS package'
arch=('x86_64')
url='https://example.org/'
license=('spdx:MIT')
depends=('dependency')
makedepends=('gcc' 'make' 'pkgconf')
source=("https://example.org/example-${pkgver}.tar.xz")
sha256sums=('REAL_SHA256')

prepare() {
  cd "${srcdir}/example-${pkgver}"
  patch -Np1 -i "${srcdir}/fix-msys.patch"
}

build() {
  cd "${srcdir}/example-${pkgver}"
  ./configure \
    --build="${CHOST}" \
    --host="${CHOST}" \
    --prefix=/usr
  make
}

check() {
  cd "${srcdir}/example-${pkgver}"
  make check
}

package() {
  cd "${srcdir}/example-${pkgver}"
  make DESTDIR="${pkgdir}" install
  install -Dm644 LICENSE \
    "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
```

Quote path expansions unless intentional word splitting is required.

### 6.1 MSYS shared-library and `CHOST` rule

The newer X11-chain recipes deliberately preserve the `CHOST` sourced by
MSYS2's makepkg configuration:

```bash
local _host="${CHOST:?CHOST unset - /etc/makepkg.conf was not sourced}"

./configure \
  --build="${_host}" \
  --host="${_host}" \
  --prefix=/usr \
  --enable-shared \
  --enable-static
```

Do not replace this value with `config.guess` output ending in `-msys`.
Libtool's Windows logic recognizes its Cygwin path, and MSYS2's patched
`libtool.m4` maps that path to `msys-*.dll`. An unrecognized `*-msys` host can
silently set `build_libtool_libs=no`, producing only a static archive even when
`--enable-shared` was requested.

A zero exit status is not sufficient. Assert the import library and DLL:

```bash
test -f "${pkgdir}/usr/lib/libExample.dll.a" || {
  error 'missing DLL import library'
  return 1
}

compgen -G "${pkgdir}/usr/bin/msys-Example-*.dll" >/dev/null || {
  error 'missing shared DLL'
  return 1
}
```

Meson packages may not use this Autotools/libtool path. Keep package-specific
Meson logic rather than forcing the Autotools flags into every recipe.

## 7. Authoring a native MINGW PKGBUILD

A conventional native package shape is:

```bash
_realname=example
pkgbase=mingw-w64-${_realname}
pkgname="${MINGW_PACKAGE_PREFIX}-${_realname}"
pkgver=1.2.3
pkgrel=1
pkgdesc='Example native Windows package (mingw-w64)'
arch=('any')
mingw_arch=('ucrt64' 'clang64')
url='https://example.org/'
license=('MIT')
depends=("${MINGW_PACKAGE_PREFIX}-dependency")
makedepends=(
  "${MINGW_PACKAGE_PREFIX}-cc"
  "${MINGW_PACKAGE_PREFIX}-cmake"
  "${MINGW_PACKAGE_PREFIX}-ninja"
)
source=("https://example.org/example-${pkgver}.tar.xz")
sha256sums=('REAL_SHA256')

build() {
  cmake -S "example-${pkgver}" -B "build-${MSYSTEM}" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="${MINGW_PREFIX}"
  cmake --build "build-${MSYSTEM}"
}

check() {
  ctest --test-dir "build-${MSYSTEM}" --output-on-failure
}

package() {
  DESTDIR="${pkgdir}" cmake --install "build-${MSYSTEM}"
  install -Dm644 "example-${pkgver}/LICENSE" \
    "${pkgdir}${MINGW_PREFIX}/share/licenses/${_realname}/LICENSE"
}
```

Rules:

- Every target-specific package dependency uses
  `${MINGW_PACKAGE_PREFIX}-...`.
- Every target installation path begins with
  `${pkgdir}${MINGW_PREFIX}`.
- Use `${MSYSTEM}` or a similarly explicit suffix for per-environment build
  directories.
- Do not hard-code `/ucrt64` or a package prefix into the recipe.
- List only architectures that actually build and run.

Common current architecture sets include:

```bash
mingw_arch=('mingw64' 'ucrt64' 'clang64' 'clangarm64')
```

and narrower sets such as:

```bash
mingw_arch=('ucrt64' 'clang64')
```

Do not advertise an architecture merely because configuration succeeds.

## 8. Sources, checksums, signatures, and patches

### 8.1 Immutable sources

Use a real checksum for release archives, NuGet files, binary bundles, and
other immutable inputs:

```bash
source=("https://example.org/project-${pkgver}.tar.xz")
sha256sums=('...')
```

For signed upstream archives, include the signature and `validpgpkeys` when
possible.

### 8.2 Git snapshots

Pin a full commit. A VCS source may conventionally use `SKIP`, but a downloaded
GitHub archive for that same commit can and should have a real checksum.

Never use a floating branch or unpinned tag for a release package.

### 8.3 Existing checksum debt

Many current MSYS2-UR recipes contain `SKIP`, and at least one historical
recipe omits `arch`. Treat those as cleanup work. Do not copy them into a new
recipe as policy.

Replace placeholder comments such as “replace SKIP with the actual checksum”
before publishing a binary built from that recipe.

### 8.4 Patch discipline

Patches should be:

- minimal;
- source-based rather than generated-output-based;
- named and applied in a deterministic order;
- accompanied by a reason; and
- removable when upstream incorporates the fix.

A multi-megabyte patch is usually evidence that generated or vendored trees
were included accidentally. Prefer a small `prepare()` transformation when it
expresses the change more clearly.

There are exceptions. Build graphs such as Ninja/GN may retain order-only
references to files that appear unused. In those cases, replacing a source file
with an empty placeholder can be safer than deleting the path and breaking the
generated graph. Document why.

Never mix one header from a newer mingw-w64 SDK into an older header set. SDK
headers are a coordinated set; this creates cascades of incompatible SAL,
WinRT, and type definitions. Select one complete toolchain and header root.

## 9. Dependencies and build order

### 9.1 Official dependencies

`makepkg -s` or `makepkg -si` can install dependencies available from configured
pacman repositories.

### 9.2 Local MSYS2-UR dependencies

Dependencies that exist only as local recipes must be built and installed
first. This repository currently has no dependency resolver or CI-generated
build order.

Build explicitly:

```bash
cd dependency
makepkg -s
pacman -U ./*.pkg.tar.zst

cd ../consumer
makepkg -s
```

Do not assume directory order is dependency order.

### 9.3 MINGW-packages dependency ordering

The upstream MINGW-packages CI derives changed package directories and sources
each PKGBUILD to inspect `depends`, `makedepends`, `pkgname`, and `provides`.
It recursively orders changed packages and warns about cycles.

When a producer and consumer change together, ensure the producer package name
matches the consumer's prefixed dependency exactly.

### 9.4 Bootstrap exceptions

Some packages, such as introspection/toolchain components, have unavoidable
bootstrap cycles or temporarily reduced feature sets. Keep the exception
local, explicit, and documented. Do not silently drop dependencies or tests.

## 10. Local build commands

### 10.1 MSYS package from this repository

Run from an MSYS2 **MSYS shell**:

```bash
pacman -Syu
pacman -S --needed base-devel git

git clone https://github.com/Kreijstal/msys2-ur.git
cd msys2-ur/libxdamage
makepkg -s
```

Install explicitly after inspection:

```bash
pacman -U ./libxdamage-*.pkg.tar.zst
```

`makepkg -si` combines the build and installation, but separate commands make
review and failure diagnosis clearer.

### 10.2 Native MinGW package

From the `MINGW-packages` package directory:

```bash
MINGW_ARCH=ucrt64 makepkg-mingw -sLf
```

For a clean release-style build:

```bash
MINGW_ARCH=ucrt64 makepkg-mingw \
  --noconfirm \
  --noprogressbar \
  --syncdeps \
  --rmdeps \
  --cleanbuild
```

Build each supported environment independently. Do not infer CLANG64 success
from UCRT64 success.

### 10.3 Keep test discovery scoped

Run project tests from the intended source tree or pass the explicit test path.
A broad `pytest` from a workspace containing unrelated historical sources can
collect incompatible tests and produce irrelevant Python 2/import errors.

Use an isolated virtual environment for Python build/test dependencies when the
host does not provide them.

## 11. Validation ladder

A package is not complete when `makepkg` exits zero. Validate every relevant
layer.

### 11.1 Source validation

- Verify the pinned commit/tag.
- Run the upstream unit tests.
- Record skipped tests and why.
- Run generated-code or smoke tests required by the build.
- Confirm no generated binary entered a source repository that forbids it.

### 11.2 Source integrity

```bash
makepkg --verifysource
```

For MINGW recipes, run through the matching `makepkg-mingw` environment if the
PKGBUILD requires its variables.

Require every source checksum to pass. `SKIP` must be a conscious VCS/signature
exception, not a placeholder.

### 11.3 Package metadata

Inspect `.PKGINFO`:

```bash
bsdtar -xOf package.pkg.tar.zst .PKGINFO
```

Check:

- package name;
- version and release;
- architecture;
- licenses;
- dependencies;
- installed size; and
- package description.

### 11.4 Archive ownership and paths

Every packaged entry should normally be owned by `root:root`:

```bash
bsdtar -tvf package.pkg.tar.zst
```

A package produced with user ownership often means a foreign `bsdtar` ignored
fakeroot's preload. Do not accept it merely because the archive was created.

Check for:

- files outside the intended prefix;
- absolute or external symlinks;
- duplicated build trees;
- accidental caches/logs; and
- missing licenses.

### 11.5 Native PE architecture and CRT

```bash
file path/to/program.exe path/to/library.dll
objdump -p path/to/program.exe | grep 'DLL Name:'
```

Confirm:

- PE32 versus PE32+;
- x86, x86-64, or AArch64;
- UCRT versus MSVCRT imports;
- bundled non-system DLLs when required; and
- no dependency on a build-host-only directory.

For a packaged bundle, compare staged runtime DLLs byte-for-byte with the
selected compiler toolchain.

### 11.6 Runtime dependency scan

MINGW-packages CI installs each produced package and runs `ntldd -R` over every
packaged EXE, DLL, and PYD. Replicate that behavior locally when possible.

Distinguish Windows system DLLs from missing third-party DLLs. A static import
scan complements but does not replace a runtime loader test.

### 11.7 Artifact assertions

Assert outputs that can silently disappear:

- shared DLL and import library;
- expected split-package files;
- generated metadata/resources;
- exact namespace-relative XBF or plugin paths;
- launcher/host colocation; and
- package-specific manifests.

Do not validate only a total file count. For a fixed binary bundle, use a
manifest of relative paths and hashes:

```bash
(
  cd bundle
  find . -type f ! -name BUNDLE-MANIFEST.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum > BUNDLE-MANIFEST.sha256
)
```

The PKGBUILD should verify it before copying files:

```bash
(cd "${bundle}" && sha256sum --check --quiet BUNDLE-MANIFEST.sha256)
```

### 11.8 Install/uninstall test

Install the exact archive that will be uploaded, query it with pacman, inspect
its file list, then uninstall it. Do not validate a staging directory while
publishing a different archive.

### 11.9 Runtime smoke/integration test

Run the smallest meaningful test:

- library link/load probe;
- command `--version` or functional invocation;
- GUI launch with bounded timeout;
- plugin/resource discovery; or
- application-specific integration gate.

Keep platform compatibility tests outside the package when they are not runtime
requirements. For example, Linux/Wine testing of a native Windows application
may use external Wine/OpenXaml components without shipping them in the package.

## 12. MINGW-packages CI behavior

The current MINGW-packages workflow covers:

- UCRT64;
- CLANG64;
- MINGW64;
- MINGW32; and
- CLANGARM64.

For each environment, CI sources the PKGBUILD and skips it when the lower-case
MSYSTEM is not in `mingw_arch`.

The build path uses clean `makepkg-mingw`, installs resulting archives, compares
pacman metadata/file lists, scans PE dependencies with `ntldd`, and removes the
package afterward.

Python packages receive additional checks, including `pip check` and reverse
package validation. Packages that install Python executables may need explicit
strip/debug handling to avoid invalid transformations.

A private CI branch may differ from an upstreamable branch only where the
private distribution requires it. Keep those differences explicit and small.

### 12.1 Hosted-runner limits

Large projects such as Qt WebEngine can exceed hosted-runner memory, disk, or
time limits. Do not respond by weakening the upstream recipe or introducing a
private binary dependency into an upstream PR.

Instead:

- split producer and consumer artifacts;
- build on an appropriate runner;
- preserve exact manifests;
- use a private MSYS2-UR build branch when necessary; and
- keep the upstream branch independently buildable once its prerequisite PRs
  land.

## 13. Upstream versus MSYS2-UR branches

Use three conceptual layers for large package work:

1. **Producer/upstream prerequisite branch** — lands first.
2. **Consumer/upstream branch** — stacked on the producer and contains no
   MSYS2-UR dependency.
3. **Private MSYS2-UR build branch** — may consume already published MSYS2-UR
   artifacts to produce private release binaries.

Never change an upstream PR so that it fetches packages from MSYS2-UR. That
would make upstream review and merge depend on a private distribution.

MSYS2-UR may rely on its own repository for private builds, but only the private
branch may encode that choice.

Before pushing, inspect the branch diff and search for private repository URLs,
release tags, or temporary artifact paths.

## 14. Binary bundle construction

A deterministic bundle should have:

- a single predictable top-level directory;
- only runtime files;
- regular files rather than host-absolute symlinks;
- a provenance file;
- a per-file SHA-256 manifest;
- licenses; and
- normalized archive ownership and timestamps.

Example:

```bash
SOURCE_DATE_EPOCH="$(git show -s --format=%ct "$commit")"

tar \
  --sort=name \
  --mtime="@${SOURCE_DATE_EPOCH}" \
  --owner=0 \
  --group=0 \
  --numeric-owner \
  --format=gnu \
  -C staging \
  -cf - bundle \
  | zstd -19 -T1 -o "bundle-${commit}.tar.zst"
```

Recreate it and confirm the checksum is stable.

Do not include:

- build logs;
- debug executables produced during investigation;
- SDK installers;
- compiler caches;
- a Wine prefix;
- test-only compatibility runtimes; or
- proprietary build tools that are not redistributable.

If a shim locates its host beside itself, install the entire application under
a private directory such as `${MINGW_PREFIX}/lib/<application>` and expose a
small wrapper in `${MINGW_PREFIX}/bin`. Do not separate colocated executables
merely to make the package layout look conventional.

## 15. Licensing and redistribution

Before upload, identify licenses for:

- the primary project;
- vendored/static dependencies;
- fonts;
- icons/artwork;
- generated code/runtime metadata; and
- any binary-only component.

Install the actual notices under the package's license directory.

If the primary source snapshot has no top-level license, do not invent a grant.
A factual `NO-LICENSE` notice can record the problem but does not authorize
redistribution. Keep the package local until the rights issue is resolved.

Build-time access is not redistribution permission. Microsoft SDK tools,
NuGet-hosted build tasks, or proprietary compilers may be usable during a local
build while remaining forbidden from the package payload.

## 16. Publishing a package release

Publishing is outward-facing and must be explicitly authorized. Building and
validating locally is not permission to push branches, edit a GitHub release,
or upload assets.

### 16.1 Pre-publication record

For every archive, record:

```bash
sha256sum ./*.pkg.tar.zst
```

Also record:

- source commit/tag;
- PKGBUILD commit;
- build environment;
- package version/release;
- test results;
- runtime scan result; and
- known limitations.

### 16.2 Stage the complete intended repository

Never run `repo-add` over only the new package when updating an aggregate
release. Doing so drops every previous package from the database.

Create a fresh staging directory and place the complete desired package set in
it. If updating an existing release, download the current package assets first,
then replace/add the intended versions and deliberately remove obsolete ones.

Example:

```bash
repo='Kreijstal/msys2-ur'
tag='x11-shared-20260731'
stage="$(mktemp -d)"

gh release download "$tag" \
  --repo "$repo" \
  --pattern '*.pkg.tar.zst' \
  --dir "$stage"

cp /path/to/new/*.pkg.tar.zst "$stage/"
```

For a signed release, also download every adjacent package signature before
regenerating the database:

```bash
gh release download "$tag" \
  --repo "$repo" \
  --pattern '*.pkg.tar.zst.sig' \
  --dir "$stage"
```

The current release has no package signatures, so that second command applies
only after signing is introduced.

Keep the obsolete archive names in an explicit manifest such as
`obsolete-assets.txt`, one exact filename per line. Remove those archives and
any signatures from the local staging set before running `repo-add`:

```bash
while IFS= read -r asset; do
  [[ -n "$asset" && "$asset" != */* && "$asset" == *.pkg.tar.zst ]] || exit 1
  rm -f -- "$stage/$asset" "$stage/$asset.sig"
done < obsolete-assets.txt
```

Do not silently retain two versions of a package unless the release is
intentionally archival. The pacman database selects one record while users can
still see/download obsolete GitHub assets, which is confusing. Removing an
archive from staging is not enough: an existing release asset with a different
versioned filename must also be deleted explicitly during the upload step.

### 16.3 Generate database and file index

From the staging directory:

```bash
cd "$stage"
rm -f msys2ur.db msys2ur.db.tar.zst \
      msys2ur.files msys2ur.files.tar.zst

repo-add msys2ur.db.tar.zst ./*.pkg.tar.zst
```

`repo-add` creates compatibility symlinks locally. GitHub release assets are
regular files, so materialize both names:

```bash
rm -f msys2ur.db msys2ur.files
cp msys2ur.db.tar.zst msys2ur.db
cp msys2ur.files.tar.zst msys2ur.files
```

The project convention is exactly these four assets:

- `msys2ur.db`
- `msys2ur.db.tar.zst`
- `msys2ur.files`
- `msys2ur.files.tar.zst`

The short and long names should be byte-identical pairs.

### 16.4 Verify database completeness

Count database records:

```bash
bsdtar -tf msys2ur.db.tar.zst \
  | cut -d/ -f1 \
  | sort -u \
  | grep -c .
```

Inspect filenames recorded in the database and confirm every selected archive
exists in the staging directory. Also confirm every intended package appears
exactly once.

At minimum:

```bash
cmp msys2ur.db msys2ur.db.tar.zst
cmp msys2ur.files msys2ur.files.tar.zst
bsdtar -tf msys2ur.db.tar.zst >/dev/null
bsdtar -tf msys2ur.files.tar.zst >/dev/null
```

Generate a release manifest:

```bash
sha256sum ./*.pkg.tar.zst \
  msys2ur.db msys2ur.db.tar.zst \
  msys2ur.files msys2ur.files.tar.zst \
  > SHA256SUMS
```

### 16.5 Future signed publication

The current release is unsigned. When signing is introduced, package signatures
must exist beside every package **before** `repo-add` runs. Produce them during
the authorized package build (`makepkg --sign` or `makepkg-mingw --sign`), stage
both the archive and its `.sig`, and verify them rather than silently signing
unknown downloaded bytes during publication:

```bash
fingerprint='FULL_OPENPGP_FINGERPRINT'
cd "$stage"

for package in ./*.pkg.tar.zst; do
  [[ -f "${package}.sig" ]] || {
    printf 'missing signature: %s\n' "${package}.sig" >&2
    exit 1
  }
  gpg --verify "${package}.sig" "$package"
done
```

Regenerate and sign both repository indexes. `--include-sigs` embeds the
available package signatures in the indexes as an additional transport path;
the standalone package `.sig` assets must still be published:

```bash
rm -f msys2ur.db msys2ur.db.tar.zst msys2ur.db.sig \
      msys2ur.db.tar.zst.sig \
      msys2ur.files msys2ur.files.tar.zst msys2ur.files.sig \
      msys2ur.files.tar.zst.sig

repo-add --sign --key "$fingerprint" --include-sigs \
  msys2ur.db.tar.zst ./*.pkg.tar.zst

cp msys2ur.db.tar.zst msys2ur.db
cp msys2ur.db.tar.zst.sig msys2ur.db.sig
cp msys2ur.files.tar.zst msys2ur.files
cp msys2ur.files.tar.zst.sig msys2ur.files.sig
```

The short-name signature is valid because its corresponding short-name database
is a byte-for-byte copy of the signed long-name database. Verify all four pairs:

```bash
cmp msys2ur.db msys2ur.db.tar.zst
cmp msys2ur.db.sig msys2ur.db.tar.zst.sig
cmp msys2ur.files msys2ur.files.tar.zst
cmp msys2ur.files.sig msys2ur.files.tar.zst.sig

gpg --verify msys2ur.db.tar.zst.sig msys2ur.db.tar.zst
gpg --verify msys2ur.files.tar.zst.sig msys2ur.files.tar.zst
```

Regenerate `SHA256SUMS` so it covers every package, package signature, database,
and database signature:

```bash
sha256sum ./*.pkg.tar.zst ./*.pkg.tar.zst.sig \
  msys2ur.db msys2ur.db.sig \
  msys2ur.db.tar.zst msys2ur.db.tar.zst.sig \
  msys2ur.files msys2ur.files.sig \
  msys2ur.files.tar.zst msys2ur.files.tar.zst.sig \
  > SHA256SUMS
```

Publish the full signing-key fingerprint and a key-distribution procedure through
a channel independent of the release assets. A checksum file signed or uploaded
by the same compromised account does not independently establish authenticity.

### 16.6 Create or update the release

A release upload command only updates an existing release. First decide whether
this is a new immutable release or an explicitly authorized update to an
existing aggregate release.

Build the unsigned asset list as follows:

```bash
release_assets=(
  ./*.pkg.tar.zst
  msys2ur.db msys2ur.db.tar.zst
  msys2ur.files msys2ur.files.tar.zst
  SHA256SUMS
)
```

For a signed release, preserve and add every signature:

```bash
release_assets+=(
  ./*.pkg.tar.zst.sig
  msys2ur.db.sig msys2ur.db.tar.zst.sig
  msys2ur.files.sig msys2ur.files.tar.zst.sig
)
```

To create a new release and tag at an explicitly reviewed commit:

```bash
commit='FULL_MSYS2_UR_COMMIT'

gh release create "$tag" \
  --repo "$repo" \
  --target "$commit" \
  --title "$tag" \
  --notes 'Added package.' \
  "${release_assets[@]}"
```

Replace the terse note with the actual package name. If the tag already exists
but has no release, omit `--target` or first verify that the tag resolves to the
intended commit.

To update an existing release, first verify that it exists:

```bash
gh release view "$tag" --repo "$repo" >/dev/null
```

`--clobber` replaces assets only when their filenames are identical. It cannot
remove an older package version because that version has a different filename.
Delete every archive listed in `obsolete-assets.txt` and its signature, if
present, from the existing release before uploading the replacement set:

```bash
remote_assets="$(
  gh release view "$tag" \
    --repo "$repo" \
    --json assets \
    --jq '.assets[].name'
)"

while IFS= read -r asset; do
  [[ -n "$asset" && "$asset" != */* && "$asset" == *.pkg.tar.zst ]] || exit 1
  for candidate in "$asset" "$asset.sig"; do
    if grep -Fqx -- "$candidate" <<<"$remote_assets"; then
      gh release delete-asset "$tag" "$candidate" \
        --repo "$repo" \
        --yes
    fi
  done
done < obsolete-assets.txt
```

Then upload after explicit authorization:

```bash
gh release upload "$tag" \
  --repo "$repo" \
  --clobber \
  "${release_assets[@]}"
```

Use `--clobber` only after confirming that replacing the existing database and
same-named assets is intended. If the aggregate release should be immutable,
create a new release instead of deleting or replacing assets.

### 16.7 Verify remote bytes

Do not trust upload success alone. Download the assets into a fresh directory
and compare hashes/bytes with the staged files:

```bash
verify="$(mktemp -d)"
gh release download "$tag" --repo "$repo" --dir "$verify"
(
  cd "$verify"
  sha256sum -c SHA256SUMS
)
```

For a signed release, also import/trust the documented public key through the
approved independent procedure and verify every package and database signature.
Confirm the remote database record count and selected package filenames again.

### 16.8 Release notes

Keep additions terse. Preferred style:

```text
Added bchunk package.
Added Qt WebEngine packages.
Added OpenTerminal package.
```

Do not turn a package addition into a wall of implementation detail. Put build
notes in this guide, the PKGBUILD, or package documentation.

## 17. Consuming the hosted repository

### 17.1 Direct installation without persistent repository trust

The current `x11-shared-20260731` release has no package signatures and no
`SHA256SUMS` asset. Therefore, there is no independently published package hash
to verify. Direct installation avoids permanently enabling a `TrustAll`
repository, but it still trusts TLS, GitHub, and control of the release account:

```bash
pacman -U ./package.pkg.tar.zst
```

Do not describe that as authenticated or independently verified. Once a future
release publishes `SHA256SUMS`, download it with the exact archive and run
`sha256sum -c SHA256SUMS` before installation. Checksums from the same unsigned
release can detect accidental corruption, but signatures rooted in an
independently distributed key are required to authenticate the publisher.

### 17.2 Persistent repository configuration

The current unsigned release can technically be configured as:

```ini
[msys2ur]
SigLevel = Optional TrustAll
Server = https://github.com/Kreijstal/msys2-ur/releases/download/x11-shared-20260731
```

Add it to `/etc/pacman.conf`, then refresh:

```bash
pacman -Syy
```

`TrustAll` means pacman is not authenticating packages cryptographically. This
must be presented as an explicit trust tradeoff, not a secure default.

The preferred future process is the signed path in section 16.5:

- sign every package before database generation;
- sign both repository indexes;
- publish all standalone signature assets;
- publish the signing fingerprint and key-distribution procedure independently;
- keep checksums as an additional integrity record; and
- remove the need for `TrustAll`.

## 18. Release/source provenance

A release tag must identify the source state it represents. Record:

- tag and commit of this repository;
- package recipes included from this repository;
- MINGW-packages branches/commits used for native packages;
- package archive checksums;
- database checksums; and
- intentionally retained external packages.

The current `master` is newer than the sole release tag, so “current recipe” and
“downloadable package” are not interchangeable statements.

A release manifest should distinguish:

- packages built from this repository;
- packages built from MINGW-packages;
- packages imported from another source; and
- obsolete archives retained only for history.

## 19. Common failures and what they mean

### Wrong build command

**Symptom:** missing `MINGW_PREFIX`, wrong dependency names, or files installed
under the wrong root.

**Cause:** using `makepkg` for a native MINGW recipe or `makepkg-mingw` for an
MSYS recipe.

**Fix:** classify the runtime and use the matching source repository/shell.

### Static library produced instead of an MSYS DLL

**Symptom:** configure and make succeed, but only `.a` exists.

**Cause:** libtool did not recognize an `*-msys` host triple.

**Fix:** preserve the `CHOST` from MSYS2's makepkg configuration and assert both
the import library and `msys-*.dll`.

### UCRT payload labelled MINGW64

**Symptom:** bundled `libstdc++-6.dll` imports `api-ms-win-crt-*`, but package is
built as MINGW64.

**Cause:** inferring CRT from the generic compiler target triplet.

**Fix:** inspect compiler configuration and PE imports; package for UCRT64.

### One modern header copied into an older mingw-w64 SDK

**Symptom:** large SAL, WinRT, WIL, or type-trait error cascades.

**Cause:** incompatible header generations were mixed.

**Fix:** use a complete, internally consistent compiler/header toolchain.

### Missing host build tool

**Symptom:** CMake cannot find tools such as `widl` despite a working compiler.

**Fix:** inventory every host and target tool separately. A compiler wrapper
alone is not a complete build environment.

### Runtime DLLs copied from the wrong compiler

**Symptom:** link succeeds, but packaged application crashes or imports an
unexpected CRT.

**Cause:** CMake found runtime DLLs beside an older compiler or wrapper path.

**Fix:** resolve runtime DLLs from the exact selected compiler and compare them
byte-for-byte before packaging.

### Binary bundle uses `SKIP`

**Symptom:** different opaque payloads can be packaged under the same version.

**Fix:** checksum the outer bundle and verify an internal relative-path
manifest.

### Local bundle absent in clean CI

**Symptom:** local build passes, clean checkout fails before `package()`.

**Cause:** source array references an untracked local archive without a URL.

**Fix:** host the immutable bundle or implement a reproducible build step.

### Package entries owned by the developer

**Symptom:** `bsdtar -tvf` shows a username instead of `root root`.

**Cause:** fakeroot state was lost, often by invoking an archive tool through a
foreign dynamic loader.

**Fix:** build entirely inside one coherent MSYS2 environment and verify archive
ownership before upload.

### `repo-add` missing or crashes on Linux

**Symptom:** command is absent or emits undefined-symbol/GLIBC errors.

**Cause:** mixing executables and libraries from a foreign rootfs.

**Fix:** run repository generation inside MSYS2 or another coherent Arch/pacman
environment. If a foreign root must be used, invoke each binary with its
matching dynamic loader and library path; never place the entire foreign
`usr/bin` ahead of host tools.

### New package uploaded but pacman cannot find it

**Symptom:** GitHub has the `.pkg.tar.zst`, but `pacman -S` cannot resolve it.

**Cause:** repository database was not regenerated/uploaded, or pacman cached
the old database.

**Fix:** rebuild and upload all four database assets, verify remote bytes, then
refresh pacman.

### Existing packages disappear from pacman

**Symptom:** database contains only the newest package(s).

**Cause:** `repo-add` ran over a partial staging set.

**Fix:** regenerate from the complete intended release package set.

### GitHub release contains stale duplicate versions

**Symptom:** database selects one version while users see multiple old archives.

**Fix:** maintain an explicit release manifest and remove obsolete assets when
updating a rolling aggregate release.

### `.db` upload is invalid or missing

**Symptom:** only `.db.tar.zst` exists remotely, or `.db` is a broken symlink
artifact.

**Fix:** replace local compatibility symlinks with regular byte-identical files
before upload.

### Upstream branch depends on MSYS2-UR

**Symptom:** an upstream PR fetches a private release asset or configures the
private repository.

**Fix:** restore the producer/consumer upstream stack and keep private repository
consumption only on the private build branch.

### Native package contains Wine

**Symptom:** a native Windows package carries Wine, a Wine prefix, or a
Wine-only compatibility runtime.

**Cause:** build/validation requirements were confused with target runtime
requirements.

**Fix:** remove Linux compatibility components. Document and test the Linux
scenario separately.

## 20. Current repository debt

The following should be improved rather than copied:

- no CI or automated release workflow;
- no dependency resolver/build-order helper;
- many `SKIP` checksums;
- inconsistent or missing `arch` declarations;
- duplicate `libxrandr` recipes;
- no checked-in package/release manifest;
- release assets not fully aligned with current recipes;
- unsigned packages and databases;
- stale package versions retained in the aggregate release; and
- no documented contribution/review checklist before this guide.

## 21. Contribution checklist

Before opening a PR:

- [ ] The recipe is in the correct source repository: MSYS recipe here, native
      recipe in MINGW-packages.
- [ ] `pkgname`, split outputs, `provides`, and `conflicts` are understood.
- [ ] Architecture declarations are accurate.
- [ ] Sources are immutable and checksummed.
- [ ] Patch files are minimal and ordered.
- [ ] Runtime and build dependencies are separated.
- [ ] The package builds from a clean tree in the matching shell.
- [ ] `check()` or equivalent project tests have run.
- [ ] Expected DLLs/import libraries/resources are asserted.
- [ ] Package metadata and file ownership were inspected.
- [ ] PE architecture, CRT, and imports were inspected for native packages.
- [ ] Licenses permit redistribution and are installed.
- [ ] No local cache, SDK payload, Wine prefix, or build log is packaged.
- [ ] No private MSYS2-UR dependency leaked into an upstream branch.
- [ ] Known limitations are documented without claiming more support than was
      tested.

## 22. Publication checklist

Before uploading:

- [ ] Explicit authorization to publish was given.
- [ ] The exact final archives were installed/tested.
- [ ] SHA-256 hashes were recorded.
- [ ] Every package archive has root ownership and safe paths.
- [ ] The complete desired repository package set is staged.
- [ ] Obsolete versions were deliberately retained or removed.
- [ ] `msys2ur.db.tar.zst` and `msys2ur.files.tar.zst` were regenerated.
- [ ] `msys2ur.db` and `msys2ur.files` are regular, byte-identical copies.
- [ ] Database record count and filenames match the intended package set.
- [ ] Release tag/source commits are recorded.
- [ ] Release notes contain only terse package-addition lines.
- [ ] Uploaded assets were downloaded and verified byte-for-byte.
- [ ] Pacman can refresh the remote database and resolve the new package.

## 23. References

- [MSYS2 packaging documentation](https://www.msys2.org/docs/package-management/)
- [MSYS2 package creation](https://www.msys2.org/wiki/Creating-Packages/)
- [Arch PKGBUILD reference](https://wiki.archlinux.org/title/PKGBUILD)
- [Current MSYS2-UR README](../README.md)
- [MSYS shared-library assertion example](../libxdamage/PKGBUILD)
- [Split-package example](../libtool/PKGBUILD)
- [XLibre split/conflict example](../xlibre-xserver/PKGBUILD)
- [MSYS2 MINGW-packages](https://github.com/msys2/MINGW-packages)
- [MSYS2-UR release](https://github.com/Kreijstal/msys2-ur/releases/tag/x11-shared-20260731)
