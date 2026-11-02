# New maintenance package validation

The source companion package `dotnet-maintenance-netstandard10`20261029-1 is
built, independently audited and installed. It adds Memory4.6.3, Unsafe6.1.2
and Tasks.Extensions4.6.3 while preserving every older installed maintenance
archive. It builds the Buffer/Vector dependencies privately and ships only the
three updates. The installed portable API/resource/identity/cache checks and
ordinary source-framework inbox selections pass.

Exact commands, the installed-check harness correction, artifact hashes and
downloaded evidence are in
[`package-results-20261029.txt`](package-results-20261029.txt).

`check-installed.py` requires the original completed build root and prepared
sources, a new consumer output and the installed source-only feed. Its portable
consumer uses the existing installed Buffer/Vector archives, checks all consumer
bytes against their actual source archives, and independently compares the three
installed update archives to the source candidate. The original build check
supplies the separate producer-cache proof.

Legacy Framework implementations, PowerShell7.6 generator integration, SDK10 and
the full dependency objective remain open.
