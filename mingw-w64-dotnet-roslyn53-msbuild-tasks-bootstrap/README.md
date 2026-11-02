# Original Roslyn5.3 NET10 MSBuild task recipe

Run `python make-source.py --update-checksum` after workflow edits,then
`makepkg --cleanbuild --force --noconfirm` on CLANG64. This cold-builds exact
MSBuild17.11.48 private compile-time prerequisites and the original NET10 task,
generates the original CompilerApiVersion target and all13 task satellites,
then tests the candidate through source MSBuild18's default task registration.

The installed Roslyn/bincore layout uses byte-verified source compiler/server
assets. Original target compilation,NET10 execution,Unicode/PDB/editorconfig/
error behavior,all434 task resource values and automatic shared-server lifecycle
are checked. Original SDK-style restore/build and additional framework/profile
requirements remain open. See [scope and provenance](workflow/README.md).

The recorded build completed all source compilations in a cold attempt,then
corrected a version-target invocation that imported an SDK layout. The focused
`ROSLYN_TASKS_RESUME_COMPILED=1 makepkg --noextract --force --noconfirm` recovery
validated original source/resource/reference/output hashes before reusing those
terminal-successful compilations. The current workflow invokes the original
version target through a no-SDK wrapper. Fresh builds use the normal clean
command;the resume option is only for an already completed compile phase.
