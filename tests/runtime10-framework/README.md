# Runtime10 complete managed implementation build

The complete prototype's source audit, linked-output audits and source-hosted
runtime probes now pass. The strict 167-assembly reference comparison has zero
missing entries, 2,096 extra entries and 248 changed entries, and remains exit 1.
No general compatibility exception list was added. Exact commands, retained
failures and evidence hashes are in
[`complete-build-results-20261029.txt`](complete-build-results-20261029.txt).
The separate pristine-source rebuild and a fresh formal package build have
completed. The isolated runtime bootstrap is installed, with all 208 manifested
bytes, its launcher, runtime discovery and three hosted probes verified.
Pacman reports 227 entries and zero altered files. Exact package commands,
limitations and 3,434 verified evidence files are recorded in
[`package-results-20261029.txt`](package-results-20261029.txt).
The remaining SDK/PowerShell dependency gates are not complete.

The complete original 190-project graph now compiles: 171 shipping managed
implementation assemblies and 19 private facade seeds, with the separately
packaged CoreLib supplying assembly 172. The original Windows JavaScript
unsupported-platform target is included. Original C#/VB inputs are retained;
resource, ASN.1, facade, versioning and library-link tasks execute from pinned
sources. The compiler/resource/linker task hosts use explicit NET8 bootstrap
profiles; this does not establish their original NET10 host profiles.

`check-built.py` audits linked API shape, forwarders, resources, symbols and
InternalCall metadata. It separately checks the original ILLink SweepStep
BeforeFieldInit optimization instead of treating that flag as public API.
`check-contracts.py` remains strict: implementation/reference differences are
reported as failures, without a general allowlist. `check-framework.py` tests
the full assembly layout using installed source CLR, CoreLib and native-library
packages. A separate JavaScript case verifies Windows PNSE behavior and the
original resource message. The bootstrap package is validated within those
checks; complete runtime compatibility remains open.

For a fresh standalone build, put the pinned runtime and Arcade archives in a
new source root and run:

```sh
bash build-all.sh NEW_SOURCE_ROOT
/usr/bin/python3 check-built.py NEW_SOURCE_ROOT/build-plan NEW_LINKED_CHECK
/usr/bin/python3 check-contracts.py NEW_SOURCE_ROOT/build-plan NEW_CONTRACT_CHECK
/usr/bin/python3 check-framework.py NEW_SOURCE_ROOT/build-plan NEW_RUNTIME_CHECK
/usr/bin/python3 stage-framework.py NEW_SOURCE_ROOT/build-plan NEW_RUNTIME_LAYOUT
```

The stage helper creates an isolated runtime layout from installed source host,
CLR/CoreLib/native components and the newly compiled managed outputs. It does
not register an SDK. Full SDK10, WindowsDesktop10, PowerShell7.6, browser/QUIC,
COM, debugger/DAC, R2R/AOT and the remaining PowerShell dependency compatibility
gates are still required by the overall goal.

This workflow evaluates every implementation project declared by the original
runtime10.0.5 `NetCoreAppLibrary.props`, excluding the separately packaged
CoreLib. It preserves the C#, Visual Basic and shim projects and records their
original compile items, project references, partial facade settings, explicit
analyzers and ASN.1 generation inputs. Relative inputs are rebound to each
original project directory; both evaluated and rebound paths are retained.

From CLANG64, with an archive root containing the materialized pinned sources
under `r/`, run:

```sh
/usr/bin/python3 prepare.py ARCHIVE_ROOT NEW_OUTPUT
bash evaluate.sh ARCHIVE_ROOT NEW_OUTPUT
/usr/bin/python3 analyze.py NEW_OUTPUT ARCHIVE_ROOT/r ARCHIVE_ROOT/runtime-v10.0.5.tar.gz
```

`analyze.py` also runs locally against downloaded evaluation JSON and the same
pinned source archive. It rejects missing files, changed original archive inputs,
unresolved private seed projects and implementation dependency cycles. Its plan
keeps the complete declared graph; it does not select a reduced subset to build.

The initial planning workflow above covers source projects, shared imports and
directory props. The complete build adds the original build-time targets and
private seeds. The original GenFacades task bootstrap prerequisite is installed;
its exact original tool profiles remain open as recorded in
[the package evidence](../runtime10-genfacades/package-results-20261028.txt).
