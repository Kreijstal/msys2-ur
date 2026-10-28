# CLANG64 build trial, 2026-10-16

PHP 8.5.11 builds and runs natively with MSYS2 CLANG64 / Clang 23.1.3 on
`win11`. The trial produces the CLI, CGI/FastCGI executable, `php8.dll`,
24 shared extension DLLs and the generated `phar.phar` command archive.

## Source and build

The source is an isolated copy of the existing MinGW port at
`~/php-dev/src` on `win11`, including its unexported port changes. It is not
an unmodified upstream tarball. The trial source and build are at:

```text
~/php-clang64-try-20261016/src
~/php-clang64-try-20261016/build
```

The full configuration enables CLI, CGI, the shared embedding runtime, OPcache,
JIT and the same extensions as the existing UCRT64 trial, plus the upstream
Zend/DL test extensions. It uses CLANG64 dependencies and makepkg compiler
flags, with `CC=clang`, `CXX=clang++`, `AR=llvm-ar`, `NM=llvm-nm` and
`RANLIB=llvm-ranlib`.

Commands run in a CLANG64 shell on `win11`:

```sh
cd ~/php-clang64-try-20261016/src
./buildconf --force
cd ..
bash configure.sh
cd build
make -j4
cd ..
timeout 180 bash check.sh
cd build
make -j4 pharcmd
./sapi/cli/php.exe -n ext/phar/phar.phar help
make -j4
```

## Fixes

Apply these patches after the existing MinGW port changes:

* `0007-build-Detect-the-Cxx-standard-library.patch`: replace the unconditional
  `-lstdc++` dependency with a cached C++ header probe. CLANG64 selects `-lc++`;
  GCC's libstdc++ remains the fallback. Configure detected libc++ and generated
  the correct link flags. The GCC header probe identified libstdc++ separately.
* `0008-phar-Honor-the-optional-loader-on-Windows.patch`: honor `-p 0` as an
  optional PEAR loader on Windows. The former code tried to open a file named
  `0`, so make ignored a failed archive-generation step. The patched generator
  produces a working Phar command requiring the built-in Phar extension.

Both saved patches were applied to copies of their original files and checked
against the exact modified files used in this trial.

## Results

* Final `make -j4` passed without ignored generation errors.
* CLI and CGI `-v` both report PHP 8.5.11, Zend 4.5.11 and OPcache 8.5.11.
* All shared modules except the deliberately excluded `php_dl_test.dll` load
  through an explicit trial INI file.
* All 19 smoke checks passed: integer width, closures, generators, exception
  unwinding, JSON, mbstring, ICU normalization, GMP, OpenSSL, sodium, PDO SQLite,
  SQLite3, DOM, GD, cURL, bzip2, FFI to the Windows C runtime, ZIP creation and
  ZIP reading.
* All 11 selected upstream PHPT tests passed, with zero skips, warnings or
  failures. They cover basic execution, closures, generators and exceptions.
* OPcache tracing JIT activated and correctly executed the hot-loop test.
* `make -j4 pharcmd` generated the archive; invoking its `help` command passed.

Scripts and collected logs are also saved locally at
`/home/kreijstal/tmp/php-clang64-try-20261016/`. The build host retains the
executables, DLLs, scripts, INI file and logs in the trial directory above.

## Packaging state

This trial does not produce or publish a pacman package. The draft PKGBUILD
still needs its first six port patches exported, a complete checksum array,
integration of patches 0007/0008, and installation/package validation. The
broader UCRT64 test-suite results do not establish CLANG64 test-suite coverage.
