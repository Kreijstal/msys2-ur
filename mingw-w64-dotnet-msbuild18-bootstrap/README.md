# MSBuild18 source bootstrap recipe

Run `python make-source.py --update-checksum` after editing the standalone
workflow, then `makepkg --cleanbuild --force --noconfirm` on CLANG64. The pinned
MSBuild/Arcade archives and three Roslyn contentFiles packages contain source;
they are validated before compilation. Every build output is created afresh.

The package builds all six primary NET10 projects,original version calculation
and53 localized satellites,then checks source/archive/output hashes,default
task registration,Unicode,parallel workers and all23597 localized values.
It installs an isolated `msbuild18-bootstrap` launcher without replacing SDK8.
See [scope and remaining SDK requirements](workflow/README.md).
