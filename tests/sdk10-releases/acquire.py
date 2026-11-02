"""Acquire original VMR Releases sources and its original Standard2 reference closure."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,sys,urllib.request
out=Path(sys.argv[1]).resolve();out.mkdir(exist_ok=True);commit='44525024595742ebe09023abe709df51de65009b';raw=f'https://raw.githubusercontent.com/dotnet/dotnet/{commit}/';api='https://api.github.com/repos/dotnet/dotnet';source_tree=json.loads(Path('/tmp/dotnet10-sources/sdk10-vmr-support/sbrp-tree.json').read_text())['tree']
packages={'System.Numerics.Vectors':'4.4.0','System.Buffers':'4.5.1','System.Runtime.CompilerServices.Unsafe':'6.0.0','System.Memory':'4.5.5','System.Threading.Tasks.Extensions':'4.5.4','Microsoft.Bcl.AsyncInterfaces':'8.0.0','System.Text.Encodings.Web':'8.0.0','System.Text.Json':'8.0.5'}
prefix='src/source-build-reference-packages/';paths={};records={}
for name,version in [*packages.items(),('System.Runtime.CompilerServices.Unsafe','4.5.3')]:
    base='src/referencePackages/src/'+name.lower()+'/'+version+'/'
    for e in source_tree:
        rel=e['path']
        if e['type']=='blob' and rel.startswith(base) and (rel.endswith('.csproj') or 'netstandard2.0/' in rel or rel.endswith(('Customizations.cs','Customizations.props'))):paths[prefix+rel]=e['sha']
for rel in ['src/referencePackages/common/IsExternalInit.cs','src/SourceBuildAssemblyMetdata.cs','src/referencePackages/Directory.Build.props','src/referencePackages/Directory.Build.targets','LICENSE.txt']:paths[prefix+rel]=None
siblings=json.loads(urllib.request.urlopen(f'{api}/contents/src?ref={commit}',timeout=30).read());entry=next(e for e in siblings if e['name']=='deployment-tools');tree=json.loads(urllib.request.urlopen(entry['git_url']+'?recursive=1',timeout=60).read())['tree']
for e in tree:
    rel=e['path']
    if e['type']=='blob' and (rel.startswith('src/Microsoft.Deployment.DotNet.Releases/') or rel in ['Directory.Build.props','Directory.Build.targets','Directory.Packages.props','eng/Versions.props','eng/Version.Details.props','eng/Version.Details.xml','LICENSE.TXT']):
        if Path(rel).suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.snk','.bin'}:continue
        paths['src/deployment-tools/'+rel]=e['sha']
for rel in ['repo-projects/deployment-tools.proj','src/arcade/src/Microsoft.DotNet.Arcade.Sdk/src/CalculateAssemblyAndFileVersions.cs','src/arcade/src/Microsoft.DotNet.Arcade.Sdk/src/GenerateResxSource.cs','src/arcade/src/Microsoft.DotNet.Arcade.Sdk/tools/GenerateResxSource.targets','src/arcade/src/Microsoft.DotNet.Arcade.Sdk/tools/Version.BeforeCommonTargets.targets']:paths[rel]=None

def fetch(item):
    rel,blob=item
    target=out/rel
    if target.exists() and blob and hashlib.sha1(b'blob '+str(target.stat().st_size).encode()+b'\0'+target.read_bytes()).hexdigest()==blob:data=target.read_bytes()
    else:
        try:
            with urllib.request.urlopen(raw+rel,timeout=60) as r:data=r.read()
        except Exception as error:raise RuntimeError(rel) from error
    git=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    if blob:assert blob==git,rel
    path=out/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return rel,dict(sha256=hashlib.sha256(data).hexdigest(),git_blob_sha1=git,vmr_url=raw+rel)
with ThreadPoolExecutor(max_workers=4) as pool:
    for rel,record in pool.map(fetch,paths.items()):records[rel]=record
(out/'source-inputs.json').write_text(json.dumps(dict(vmr_commit=commit,files=records,original_reference_package_versions=packages,original_releases_framework='netstandard2.0',published_implementation_binaries_downloaded=False),indent=2)+'\n');print('PASS acquired',len(records),'original VMR source files for Releases and original reference-only dependency closure')
