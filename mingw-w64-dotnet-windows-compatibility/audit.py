"""Compare every dependency group with the published metadata-only baseline."""
from pathlib import Path
import argparse,hashlib,json,xml.etree.ElementTree as E,zipfile
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path);args=parser.parse_args()
root=args.root.resolve();here=Path(__file__).resolve().parent
ns={'n':'http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd'}
def metadata(data):
 tree=E.fromstring(data);uri=tree.tag.partition('}')[0]+'}' if tree.tag.startswith('{') else '';m=tree.find(uri+'metadata');groups={}
 for group in m.find(uri+'dependencies'):
  tfm=group.get('targetFramework').replace('.NETStandard','netstandard').replace('.NETCoreApp','net')
  groups[tfm]={d.get('id'):(d.get('version').strip('[]').rstrip(','),d.get('exclude')) for d in group}
 return m,uri,groups
published,_,wanted=metadata((here/'published.nuspec').read_bytes())
package=root/'feed/microsoft.windows.compatibility.8.0.31.nupkg';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with zipfile.ZipFile(package) as z:
 assert not any(name.lower().endswith(('.dll','.exe','.so','.pdb','.nupkg')) for name in z.namelist())
 actual,uri,got=metadata(z.read('Microsoft.Windows.Compatibility.nuspec'));assert got==wanted,(got,wanted)
 assert actual.findtext(uri+'id')=='Microsoft.Windows.Compatibility' and actual.findtext(uri+'version')=='8.0.31'
 assert actual.find(uri+'repository').get('commit')=='337963009d48a3016b50172b451b4e80f78791a7'
 assert z.read('PACKAGE.md')==(root/'source/src/Microsoft.Windows.Compatibility/src/PACKAGE.md').read_bytes()
 assert z.read('Icon.png')==(root/'Icon.png').read_bytes()
 assert z.read('LICENSE')==(root/'source/LICENSE').read_bytes()
 assert z.read('Arcade-LICENSE.TXT')==(root/'Arcade-LICENSE.TXT').read_bytes()
 actual_files={name:hashlib.sha256(z.read(name)).hexdigest() for name in z.namelist()}
assert len(wanted)==5 and sum(map(len,wanted.values()))==191
report=dict(package_sha256=sha(package),full_original_and_published_dependency_groups_match=True,framework_group_counts={k:len(v) for k,v in wanted.items()},total_dependency_entries=191,library_payloads=0,nuget_entry_sha256=actual_files,published_metadata_only_baseline_sha256=sha(here/'published.nuspec'),fresh_source_closure_verified=False,full_dependency_goal_complete=False)
(root/'package-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS complete original/published five-framework191 dependency entries, exact source readme/icon/licenses and zero implementation libraries')
