# Shared system-V8 GN integration

This integration targets the Chromium 140 / V8 14.0.365.10 baseline used by
Qt WebEngine 6.11.2. Apply the project's MinGW port first. The same integration
entry point can then be used in Chromium, Electron or Qt's Chromium checkout
when its source version and resolved engine configuration match the SDK.
It does not claim compatibility across different V8 revisions or ABIs.

```sh
python chromium-patches/v8/apply.py /path/to/chromium
```

`apply.py` retains the bundled implementation inside the false branch and adds
`use_system_v8` (default false). It inlines the maintained GN fragment because
GN imports cannot access the caller's resolved local feature variables. Apply
to a fresh source tree; repeated application is rejected.
Bundled generator settings are evaluated only in bundled mode; system mode
uses the package's installed generators and startup snapshot.

Configure a fresh output directory using the same engine feature profile as
the producer, plus:

```gn
use_system_v8 = true
system_v8_runtime = "ucrt64"
# Optional; otherwise pkg-config --variable=manifest v8 discovers it.
system_v8_manifest = "E:/msys64/ucrt64/share/v8/build-manifest.json"
```

`gn gen` compares the exact version/revision, runtime, resolved V8/cppgc
configuration and public/private definitions. Missing SDK payloads or a
mismatch fail generation. There is no fallback to bundled V8. The manifest is
a GN regeneration dependency, so package changes invalidate the graph.

The original `v8`, `cppgc`, `cppgc_base`, `v8_heap_base`, header, platform and
base-library labels forward to installed libraries and SDK headers. The main
V8 DLL owns cppgc and heap-base; the consumer compiles neither implementation.
Matching installed generators are copied into their expected output locations.
Chromium's Perfetto runtime target uses the SDK's tracing DLL as well, so V8
event registration and browser tracing sessions share one tracing muxer. Its
other processor, IPC, JSON and public-header dependencies remain in the
consumer graph. The bundled branch keeps the original runtime target.
The gate also compares Perfetto's public headers and tracks them as GN
regeneration inputs. It ignores line endings and the SDK's specific registry
export-linkage fix; other header differences fail generation.
The `perfetto/test/` testonly helper target is outside this runtime ABI check.
Its headers are restored separately for the `content_shell` harness.
Consumer-specific context snapshots remain consumer-generated. This initial
profile embeds the default V8 startup snapshot in its DLL. The
`run_mksnapshot_default` label copies the matching, real SDK startup blob;
it does not stand in for a custom consumer snapshot. Qt's current MinGW port
disables its context snapshot in its final GN overrides, and the control
uses those same settings.

The gate compares all 129 resolved engine and ICU data flags and release definitions.
The DLL-specific `V8_TLS_USED_IN_LIBRARY` definition is normalized for the
bundled control, then explicitly provided to shared consumers. Other
differences fail generation. If the checkout restricts `exec_script`, the
installer adds only the V8 BUILD file to the existing allowlist.

This layer does not port unrelated Chromium Windows code to MinGW. The
existing project-specific toolchain and platform patches remain prerequisites.
Acceptance requires the real consumer build with bundled implementation and
header directories inaccessible, not just successful GN generation.
