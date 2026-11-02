# Maintainer: Kreijstal <rainb@tfwno.gf>
_realname=dotnet-sdk8-servicing
pkgbase=mingw-w64-${_realname}
pkgname=("${MINGW_PACKAGE_PREFIX}-${_realname}")
pkgver=8.0.131
pkgrel=3
pkgdesc='Audited source SDK8 with source-built8.0.31 apphost and runtime packs (mingw-w64)'
arch=('any')
mingw_arch=('clang64')
url='https://github.com/dotnet/sdk'
license=('spdx:MIT' 'spdx:Apache-2.0' 'spdx:BSD-3-Clause')
provides=("${MINGW_PACKAGE_PREFIX}-dotnet-sdk=${pkgver}-${pkgrel}")
conflicts=("${MINGW_PACKAGE_PREFIX}-dotnet-sdk")
depends=("${MINGW_PACKAGE_PREFIX}-dotnet-runtime=8.0.131"
         "${MINGW_PACKAGE_PREFIX}-dotnet-runtime8-servicing=8.0.31-3"
         "${MINGW_PACKAGE_PREFIX}-dotnet-targeting8-servicing>=8.0.31-2"
         "${MINGW_PACKAGE_PREFIX}-dotnet-sdk-netanalyzers=8.0.0.preview26274.2")
makedepends=("${MINGW_PACKAGE_PREFIX}-dotnet-sdk>=8.0.131-2"
             "${MINGW_PACKAGE_PREFIX}-cc" "${MINGW_PACKAGE_PREFIX}-cmake"
             "${MINGW_PACKAGE_PREFIX}-ninja" "${MINGW_PACKAGE_PREFIX}-llvm"
             'mingw-w64-ucrt-x86_64-mono=6.12.0.199' 'python' 'patch' 'make')
options=('!strip' '!lto' '!buildflags')
# The SDK input is our unchanged, audited source-bootstrap package, built by
# mingw-w64-dotnet-bootstrap from the Mono seed. No vendor SDK binaries enter.
source=('mingw-w64-clang-x86_64-dotnet-sdk-8.0.131-2-any.pkg.tar.zst'
        'runtime-v8.0.31.tar.gz::https://codeload.github.com/dotnet/runtime/tar.gz/refs/tags/v8.0.31'
        "dotnet-bootstrap-3cbf21078968e2290a54ab093392b4dfeb1c6f1f.tar.gz::https://github.com/Kreijstal/msys2-ur/releases/download/x11-shared-20260731/dotnet-bootstrap-3cbf21078968e2290a54ab093392b4dfeb1c6f1f.tar.gz"
        'dotnet-runtime8-servicing-source-3.tar.gz'
        'dotnet-sdk8-servicing-source-1.tar.gz'
        'README.md')
noextract=('mingw-w64-clang-x86_64-dotnet-sdk-8.0.131-2-any.pkg.tar.zst'
           'runtime-v8.0.31.tar.gz'
           'dotnet-bootstrap-3cbf21078968e2290a54ab093392b4dfeb1c6f1f.tar.gz')
sha256sums=('3e23ceeddb31efcd60b25238115deda3daf7de6ba4b42db143974e9b031c04b5'
            'b32a56a29cc0248bed219e1c7ef026bf8f006d997f5d6346382e63a22ecd9070'
            '75bea2026b90c7f4d5f88279c4ff25ca07b4a6eb0e435df90a41c6f485f773c6'
            '1901796a07f37c06c6a5423cce5ce67b98fd300a7201f9a055e998f30d062356'
            'ae242a43aebcbbe6f5099c4410ce95bc7dcdcc034fc7ffff3fd5155b866131b5'
            '2c72e9f1b9ce8a353ba444cf9dec389b29270349d47332d2b9ff7786628c079c')

build() {
  bash "$srcdir/sdk-servicing/build-host.sh" "$srcdir/servicing" \
    "$srcdir/runtime-v8.0.31.tar.gz" \
    "$srcdir/dotnet-bootstrap-3cbf21078968e2290a54ab093392b4dfeb1c6f1f.tar.gz" \
    "$srcdir/prepared"
  /usr/bin/python3 "$srcdir/sdk-servicing/stage-sdk.py" \
    "$srcdir/mingw-w64-clang-x86_64-dotnet-sdk-8.0.131-2-any.pkg.tar.zst" \
    "$srcdir/prepared" "$srcdir/sdk-stage"
}

check() {
  /usr/bin/python3 "$srcdir/sdk-servicing/prepare-check-layout.py" "$srcdir/sdk-stage" "$srcdir/sdk-check-root"
  bash "$srcdir/sdk-servicing/check-packs.sh" "$srcdir/sdk-check-root" "$srcdir/sdk-pack-check"
}

package() {
  mkdir -p "$pkgdir$MINGW_PREFIX"
  cp -a "$srcdir/sdk-stage/clang64/." "$pkgdir$MINGW_PREFIX/"
  local doc="$pkgdir$MINGW_PREFIX/share/doc/$_realname"
  mkdir -p "$doc"
  install -m644 "$srcdir/README.md" "$doc/"
  install -m644 "$srcdir/sdk-stage/source-sdk-servicing.json" "$doc/"
  for file in source-inputs version-build-inputs file-version-adapters; do
    install -m644 "$srcdir/prepared/$file.json" "$doc/host-$file.json"
  done
  install -m644 "$srcdir/sdk-servicing/check-packs.sh" "$doc/"
  install -m644 "$srcdir/sdk-servicing/audit-packs-check.py" "$doc/"
  install -m644 "$srcdir/sdk-servicing/inputs/source-inputs.json" "$doc/runtime-list-source-inputs.json"
  local licenses="$pkgdir$MINGW_PREFIX/share/licenses/$_realname"
  install -Dm644 "$srcdir/prepared/m/src/runtime-8.0.31-native/LICENSE.TXT" "$licenses/runtime-LICENSE.TXT"
  install -m644 "$srcdir/prepared/m/src/runtime-8.0.31-native/THIRD-PARTY-NOTICES.TXT" "$licenses/runtime-THIRD-PARTY-NOTICES.TXT"
  install -m644 "$srcdir/sdk-servicing/inputs/LICENSE.TXT" "$licenses/Arcade-LICENSE.TXT"
}
