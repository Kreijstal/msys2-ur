NuGet.Client 6.9.1 Core libraries
===============================

These eleven split packages preserve the complete original NuGet Core library
projects at commit 623fde83a3cd73cb479ec7fa03866c6116894dbf (release6.9.1.3).
Production C# is unchanged. The original DotNetBuildFromSource configuration
selects net8.0, original public signing, BuildRTM=true and BuildNumber=3.
BUILD_SOURCEVERSION and SourceRevisionId preserve the original double-commit
informational version. NuGet's SDK-private implementations are not replaced.

Dependencies use source Extensions6.0.0, Newtonsoft.Json13.0.4, Pkcs8.0.1 and
ProtectedData8.0.0. The original central ProtectedData declaration selects8.0.0;
other substitutions use upstream source-build version properties. Original
multiline resources use XML character references to preserve the published
Windows CRLF messages through the SDK XML reader. Build metadata overlays and
original/prepared resource hashes are recorded explicitly.

The compiler-input gate requires all1288 original C# compilation items,
including13 unchanged shared files per project, plus only the22 SDK assembly
metadata inputs. It also records actual resource/schema inputs and resolved
source references. Original projects, all1145 project C# files, shared source,
resources, signing key, archive and recipe inputs have pinned hashes.

Each NuGet contains lib/net8.0 implementation and ref/net8.0 metadata assemblies,
XML documentation, original Apache2.0 license/notices, this README and its
source-build inventory. Exact dependency versions match the selected source
closure. Native MSYS2 dependencies preserve the same direct graph.

check.sh uses a new consumer/cache and source feeds only. It verifies all7845
published Core public/protected API declarations, original signing/assembly/file/
informational identities and all807 strings in13 resource manifests. Published
DLLs supplied the metadata baselines only; they never compile or execute here.
Compiler reference and runtime implementation bytes must match package inventories.

Owned behavior checks exercise package creation/reading, version boundaries,
local stable/prerelease discovery/download, original RestoreRunner dependency
resolution, global-cache/assets and Unicode extraction. An ephemeral loopback
V3 feed tests actual401 credential-provider authentication, flat-container
versions/downloads and404 handling. An in-memory certificate tests original
NuGet author signing, CMS signature verification, package integrity and tamper
rejection. No machine trust or verification policy is changed.

This covers the eleven Core libraries needed by PSResourceGet. Separate NuGet
command-line/build-task/Visual Studio projects, remote service/authentication
matrices, PSResourceGet's Azure/MSAL/ClientModel/JSON closure and full PowerShell
packaging remain open. The actual source CLR is8.0.0; package/ref aliases do not
supply later servicing changes.
