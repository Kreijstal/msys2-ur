from pathlib import Path
import json,hashlib,sys,xml.etree.ElementTree as E
source=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve();projects={}
for label,leaf in [('analyzers','Analyzers'),('codefixes','CodeFixes')]:
 original=source/'src/PublicApiAnalyzers/Core'/leaf/('Microsoft.CodeAnalysis.PublicApiAnalyzers'+('.CodeFixes' if label=='codefixes' else '')+'.csproj')
 selected=set(original.parent.rglob('*.cs'));imports=set();references=[]
 def collect(path):
  if path in imports:return
  imports.add(path)
  for g in E.parse(path).getroot():
   kind=g.tag.rsplit('}',1)[-1]
   if kind=='Import':
    rel=g.get('Project').replace('\\','/');assert '$(' not in rel;collect((path.parent/rel).resolve())
   elif kind=='ItemGroup':
    cond=g.get('Condition')
    if cond=="'$(HasIOperation)' == 'true'":continue
    assert cond in [None,"'$(IsTestProject)' != 'true' and '$(NonShipping)' != 'true'"],cond
    for n in g:
     tag=n.tag.rsplit('}',1)[-1]
     if tag=='Compile':
      rel=n.get('Include').replace('$(MSBuildThisFileDirectory)',str(path.parent)+'/').replace('\\','/');assert '$(' not in rel and '*' not in rel;selected.add((Path(rel) if Path(rel).is_absolute() else path.parent/rel).resolve())
     if tag=='PackageReference':references.append(dict(id=n.get('Include'),version=n.get('Version')))
 collect(original)
 assert all(p.is_file() and p.is_relative_to(source) for p in selected)
 projects[label]=dict(assembly=original.stem,bootstrap_reference_MicrosoftCodeAnalysisVersion='4.4.0',original_source_capability_guards_preserved=True,original_framework=E.parse(original).findtext('.//TargetFramework'),original_MicrosoftCodeAnalysisVersion=E.parse(original).findtext('.//MicrosoftCodeAnalysisVersion'),sources={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(selected)},original_imports={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in imports},original_package_references=references,resource_files={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in original.parent.glob('*.resx')})
output.write_text(json.dumps(projects,indent=2)+'\n');print({k:(v['original_framework'],len(v['sources']),v['original_package_references']) for k,v in projects.items()})
