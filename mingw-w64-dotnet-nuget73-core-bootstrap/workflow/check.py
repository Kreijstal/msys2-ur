"""Compile and execute original API baselines plus foundation runtime checks."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys

plan,build,out,localization=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix()
binary=out/'bin';shutil.copytree(build/'bin',binary);baselines=out/'baselines';baselines.mkdir();originals={}
names=['NuGet.Versioning','NuGet.Frameworks','NuGet.Common','NuGet.LibraryModel']
for name in names:
    parts=[]
    for label in ['Shipped','Unshipped']:
        p=source/'src/NuGet.Core'/name/('PublicAPI.'+label+'.txt');parts.append(p.read_text(encoding='utf-8-sig'));originals[p.relative_to(source).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    (baselines/(name+'.txt')).write_text('\n'.join(parts)+'\n')
upstream=source/'test/NuGet.Core.Tests/NuGet.Versioning.Test/VersionRangeTests.cs';text=upstream.read_text();section=text.split('public void VersionRange_PrettyPrintTests',1)[0]
vectors=[json.loads('['+m+']') for m in re.findall(r'\[InlineData\(("[^"\n]*", "[^"\n]*")\)\]',section)];assert len(vectors)==19,len(vectors)
(baselines/'upstream-range-vectors.json').write_text(json.dumps(vectors)+'\n');originals[upstream.relative_to(source).as_posix()]=hashlib.sha256(upstream.read_bytes()).hexdigest()
compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap'
for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']:shutil.copyfile(compiler/(name+'.dll'),binary/(name+'.dll'))
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
args=['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(binary/'Check.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs+[binary/(n+'.dll') for n in names+['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']]]+['"'+native(here/n)+'"' for n in ['Check.cs','CheckApi.cs']]
rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');(binary/'Check.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));commands=[]
for label,command in [('compile',[host,compiler/'csc.dll','-noconfig','@'+native(rsp)]),('execute',[host,binary/'Check.dll',source,refs[0].parent,baselines,out/'owned-work',localization])]:
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_api_and_vector_input_sha256=originals,original_upstream_range_vectors=len(vectors),full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print((out/'execute.log').read_text(encoding='utf-8'))
