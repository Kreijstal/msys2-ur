# V8 / Chromium acceptance

Run the configuration gate tests without building the engine:

```sh
python tests/v8-chromium/test_sdk.py -v
python tests/v8-chromium/test_gn_gate.py -v
python tests/v8-chromium/test_link_evidence.py -v
gn format --dry-run chromium-patches/v8/system_v8_targets.gni
bash -n mingw-w64-v8/PKGBUILD
```

The GN tests use clearly identified temporary fixtures, not binary validation.
They verify that external mode omits bundled implementation sources, that
bundled mode still generates without an SDK, and that incompatible packages
fail during GN generation.

After staging or installing the real package, run native UCRT64 consumers from
a directory outside the producer source/build tree:

```sh
python tests/v8-chromium/run_sdk.py --prefix E:/msys64/ucrt64 --out E:/v8-sdk-check
```

This checks payload hashes and compiles/runs shared and monolithic embedders,
cppgc allocation/tracing/finalization and heap-base exports. The embedder checks
JavaScript, asynchronous jobs, WebAssembly, ICU and snapshot creation/restoration.
Both linkage modes also record real V8 GC events through Perfetto. The static
executables must not import any V8 component DLL.
The installed `mksnapshot` must also produce a nonempty consumer snapshot.

For the consumer acceptance, first build the bundled `content_shell` control.
Qt's source distribution omits files required by that target. Restore its
missing harness inputs from checksum-pinned upstream sources before building:

```sh
python tests/v8-chromium/restore_control.py --chromium /path/to/chromium \
  --cache /path/to/source-cache
```

For the Qt 6.11.2 MinGW control, apply the existing WebEngine port first,
including the libaom configuration rebase for 6.11.2. The additional fixes in
`control-mingw/` numbered 0126–0129 come from the newer local Qt WebEngine core recipe; their
original paths and hashes are recorded in `control-mingw/provenance.json`.
Patch 0126 omits a zstd hunk already provided by the earlier control patches;
the provenance records both the original and adapted checksums.
Apply them to both consumers, in order, from the Qt source root:

```sh
for fix in /path/to/tests/v8-chromium/control-mingw/*.patch; do
  patch --batch --forward --fuzz=0 -p1 -i "$fix"
done
```

These fix missing Windows source/link inputs, MinGW COM implementations,
shell PIDL ownership without ATL, and a Windows macro collision in Blink's
image encoder. Patch 0126 also retains the existing port's limitations for
preview DirectComposition interfaces, NPU/DirectML discovery, XPS output and
native geolocation. Use the same patches for bundled and system V8 so the
comparison keeps those platform settings identical. The newer recipe's
separate protected-memory and Qt sandbox workarounds are not in this series.
Patch 0132 restricts GoogleTest's `/wd4800` compiler option to MSVC; GCC builds
retain the same GoogleTest sources and definitions.
Patch 0133 supplies the documented roaming-profile flag missing from older
MinGW headers, retaining Chromium's existing policy profile classification.

The helper preserves existing Qt security backports and MinGW port changes.
`control-inputs.json` records every restored archive or individual file.
The restored inputs include policy templates and Perfetto's test helpers,
which Qt's archive omits even though `content_shell` needs them.
Gitiles archives use the same complete-payload SHA-256 verifier as the producer because
their tar timestamps change on download. Gitiles individual files are decoded
from base64 before their byte checksum is verified.

Then configure a fresh system-V8 output with the same ABI settings, apply the
integration and make bundled `v8/include`, `v8/src` and equivalent generated
implementation inputs inaccessible. Retain the GN metadata. Build the system
consumer with compilation database export and retained linker response files:

```sh
gn gen out/system --export-compile-commands
ninja -C out/system -d keeprsp -k0 content_shell
python tests/v8-chromium/audit_build.py --chromium /path/to/chromium \
  --out /path/to/chromium/out/system \
  --manifest E:/msys64/ucrt64/share/v8/build-manifest.json
python tests/v8-chromium/run_shell.py \
  --bundled /path/to/out/bundled/content_shell.exe \
  --system /path/to/out/system/content_shell.exe --evidence /path/to/evidence
python tests/v8-chromium/run_tracing.py \
  --bundled /path/to/out/bundled/content_shell.exe \
  --system /path/to/out/system/content_shell.exe \
  --manifest E:/msys64/ucrt64/share/v8/build-manifest.json \
  --evidence /path/to/evidence
```

The audit rejects compiled bundled engine/collector sources and a second
Perfetto tracing muxer, requires an
external V8 import library in the executable's actual linker command or its
retained response files, and an actual V8 DLL import
in the initial non-component consumer, and checks deployed component hashes.
The web test covers JS, async, Wasm, ICU, DOM wrappers and GC. Publication also
requires V8 GC events to reach the browser's tracing session and each system
renderer to load the package's actual V8 DLL. The tracing check requires the
native Python `websocket-client` module. Record the resolved GN flags,
compiler/link evidence and these results; passing fixture tests alone is
insufficient.

`-k0` lets independent build actions finish when a source fails, collecting
compiler errors for a repair batch. Acceptance still requires a successful
build and every runtime check above.
