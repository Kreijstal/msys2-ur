"""Inspect exact SDK-selected published analyzer metadata; never execute target code."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
r=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir();version='8.0.0-preview.26274.2'
package=r/('microsoft.codeanalysis.netanalyzers.'+version+'.nupkg');folder=r/'published';folder.mkdir()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
assemblies={};assets={}
with zipfile.ZipFile(package) as z:
 z.extractall(folder)
 for name in z.namelist():
  if name.startswith(('buildTransitive/','build/','editorconfig/','rulesets/','documentation/')) and not name.endswith('/'):
   assets[name]=z.read(name).decode('utf-8-sig').replace('\r\n','\n')
  if name.endswith('.dll') and not name.endswith('.resources.dll'):
   target=folder/name;entry={}
   for tool,key in [('Api','api'),('Inventory','inventory'),('Metadata','metadata')]:
    args=[native(Path('/clang64/lib/dotnet/dotnet.exe')),native(r/'metadata'/tool/'bin/Release/net8.0/Tool.dll')]
    if key=='api':args.append(native(Path('/clang64/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0')))
    args.append(native(target));entry[key]=json.loads(subprocess.check_output(args,text=True))
   if target.name in assemblies:assert assemblies[target.name]==entry,target.name
   assemblies[target.name]=entry
(out/'ExpectedAssemblies.json').write_text(json.dumps(assemblies,indent=2)+'\n')
(out/'ExpectedGeneratedAssets.json').write_text(json.dumps(assets,indent=2)+'\n')
(out/'published-metadata-provenance.json').write_text(json.dumps(dict(package='Microsoft.CodeAnalysis.NetAnalyzers',version=version,url='https://pkgs.dev.azure.com/dnceng/public/_packaging/dotnet8/nuget/v3/flat2/microsoft.codeanalysis.netanalyzers/'+version+'/microsoft.codeanalysis.netanalyzers.'+version+'.nupkg',sha256=hashlib.sha256(package.read_bytes()).hexdigest(),source_commit='0963af6bfc2a3d5083faa2b7c1c91a4eee29a6f4',sdk_manifest='https://github.com/dotnet/sdk/blob/v8.0.131/eng/Version.Details.xml',inspection='PEReader/MetadataReader/Roslyn metadata symbols only; no target code execution'),indent=2)+'\n')
for name,entry in assemblies.items():
 print(name,entry['metadata']['version'],entry['metadata']['versions'],'analyzers',len(entry['inventory']['analyzers']),'fixers',len(entry['inventory']['code_fixes']),'IDs',len(entry['inventory']['diagnostic_ids']),'API',len(entry['api']['api']),'resources',list(entry['metadata']['resources']))
print('Build/documentation asset count',len(assets))
