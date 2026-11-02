"""Package original references with full pinned publisher dependency metadata."""
from pathlib import Path
import hashlib,json,sys,zipfile
import xml.etree.ElementTree as E
out=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
source=out/'standard-18a36291e48808fa7ef2d00a764ceb1ec95645a5'
publisher=here/'inputs/NETStandard.Library.publisher.nuspec'
assert hashlib.sha256(publisher.read_bytes()).hexdigest()=='f0c9c450d3c84f9c6c2728834843731a09e259d3aa784b65a557fbd370d73d77'
ns={'n':'http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd'}
E.register_namespace('',ns['n'])
spec=E.parse(publisher).getroot();md=spec.find('n:metadata',ns)
assert md.findtext('n:id',namespaces=ns)=='NETStandard.Library'
assert md.findtext('n:version',namespaces=ns)=='2.0.3'
groups=md.findall('n:dependencies/n:group',ns)
assert len(groups)==20 and sum(len(g) for g in groups)==337
baseline=json.loads((source/'pkg/baseline/packageIndex.json').read_text())['Packages']
for group in groups:
 for dep in group:
  assert baseline[dep.get('id')]['BaselineVersion']==dep.get('version'),dep.attrib
namespace='{'+ns['n']+'}'
license_url=md.find('n:licenseUrl',ns);md.remove(license_url)
E.SubElement(md,namespace+'license',type='file').text='LICENSE.TXT'
E.SubElement(md,namespace+'repository',type='git',url='https://github.com/dotnet/standard',commit='18a36291e48808fa7ef2d00a764ceb1ec95645a5')
template=(source/'netstandard/pkg/targets/netstandard/NETStandard.Library.targets').read_text()
facades=';'.join('$(MSBuildThisFileDirectory)ref\\'+p.name for p in sorted((out/'ref').glob('*.dll')) if p.name!='netstandard.dll')
targets=template.replace('#VERSION#','2.0.3').replace('#NETSTANDARDFACADES#',facades)
assert '#' not in targets
feed=out/'feed';feed.mkdir(exist_ok=True)
files={'NETStandard.Library.nuspec':E.tostring(spec,encoding='utf-8',xml_declaration=True),
       'LICENSE.TXT':(source/'LICENSE.TXT').read_bytes(),
       'lib/netstandard1.0/_._':b'',
       'build/netstandard2.0/NETStandard.Library.targets':targets.encode()}
for p in sorted((out/'ref').glob('*.dll')):files['build/netstandard2.0/ref/'+p.name]=p.read_bytes()
assert sum(n.endswith('.dll') for n in files)==113
with zipfile.ZipFile(feed/'netstandard.library.2.0.3.nupkg','w',zipfile.ZIP_DEFLATED) as z:
 for name,data in sorted(files.items()):
  info=zipfile.ZipInfo(name,date_time=(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
  z.writestr(info,data)
(out/'package-metadata.json').write_text(json.dumps(dict(original_dependency_groups=20,original_dependency_edges=337,original_unique_dependencies=44,publisher_nuspec_sha256=hashlib.sha256(publisher.read_bytes()).hexdigest(),package_files_sha256={n:hashlib.sha256(d).hexdigest() for n,d in files.items()},all_dependency_versions_match_original_source_baseline=True),indent=2)+'\n')
print('PASS all 20 original dependency groups/337 edges and 113 source reference assets packaged')
