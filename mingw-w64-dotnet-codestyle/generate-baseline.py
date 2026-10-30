"""One-time published baseline extraction. Target binaries are metadata-only inputs."""
import os
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(exist_ok=True)
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
result={};assets={};provenance={}
for language in ['CSharp','VisualBasic']:
 package=root/(language.lower()+'.4.9.2.nupkg');folder=root/'published'/language
 with zipfile.ZipFile(package) as z:
  provenance[language]=dict(url='https://api.nuget.org/v3-flatcontainer/microsoft.codeanalysis.'+language.lower()+'.codestyle/4.9.2/microsoft.codeanalysis.'+language.lower()+'.codestyle.4.9.2.nupkg',sha256=hashlib.sha256(package.read_bytes()).hexdigest())
  assets[language]={name:z.read(name).decode('utf-8-sig').replace('\r\n','\n') for name in z.namelist() if name.startswith('build/')}
  for name in z.namelist():
   if name.endswith('.dll') and not name.endswith('.resources.dll'):
    target=folder/name;item={}
    for tool,key in [('InspectMetadata','metadata'),('InspectInventory','inventory'),('InspectApi','api')]:
     args=[native(Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/dotnet.exe')),native(root/'metadata'/tool/'bin/Release/net8.0/Tool.dll')]
     if key=='api':args.append(native(Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0')))
     args.append(native(target));item[key]=json.loads(subprocess.check_output(args,text=True))
    if target.name in result:assert result[target.name]==item,target.name
    result[target.name]=item
(out/'ExpectedAssemblies.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'ExpectedBuildAssets.json').write_text(json.dumps(assets,indent=2)+'\n')
(out/'published-metadata-provenance.json').write_text(json.dumps(dict(packages=provenance,inspection='PEReader/MetadataReader and Roslyn metadata symbols only; no target code execution',source_commit='9934fb9e3527e1c0c51314e57d4aab30f97e8f9e'),indent=2)+'\n')
print('Captured independent baseline for',len(result),'assemblies and',sum(map(len,assets.values())),'build text assets')
