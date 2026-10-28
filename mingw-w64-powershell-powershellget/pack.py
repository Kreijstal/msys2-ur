"""Gate all 16 original module assets and create the complete source PSModule package."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as E
import zipfile

def normalize(data, name):
    text=data.decode('utf-16' if data[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig').replace('\r\n','\n')
    text=re.split(r'(?m)^.*?SIG # Begin signature block.*$',text,maxsplit=1)[0].rstrip()+'\n'
    if name=='PowerShellGet.psd1': text='\n'.join(line.lstrip() for line in text.splitlines())+'\n'
    return text.encode()

prepared,output=(Path(p).resolve() for p in sys.argv[1:])
here=Path(__file__).resolve().parent
gold=json.loads((here/'published-provenance.json').read_text())
module=prepared/'module'
shutil.copytree(prepared/'source/dist/PowerShellGet',module)
# The gallery layout includes the same original English resource in both locations.
(module/'en-US').mkdir()
shutil.copyfile(module/'PSGet.Resource.psd1',module/'en-US/PSGet.Resource.psd1')
assets={p.relative_to(module).as_posix():p.read_bytes() for p in module.rglob('*') if p.is_file()}
assert set(assets)==set(gold['module_assets']), 'complete module asset inventory mismatch'
for name,data in assets.items():
    expected=gold['module_assets'][name]
    assert hashlib.sha256(normalize(data,name)).hexdigest()==expected['normalized_sha256'],name
    if expected['source']:
        assert data==(prepared/'source'/expected['source']).read_bytes(),name
record=json.loads((prepared/'source-build.json').read_text())
record['module_files']={name:hashlib.sha256(data).hexdigest() for name,data in sorted(assets.items())}
record['published_comparison']='All 16 module files match normalized original published contents; manifest leading indentation also normalized.'
(prepared/'source-build.json').write_text(json.dumps(record,indent=2)+'\n')
root=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd')
meta=E.SubElement(root,'metadata')
for name,value in dict(id='PowerShellGet',version='2.2.5',authors='Microsoft Corporation',description='Complete source PowerShellGet repository/module/script management module.',requireLicenseAcceptance='false',readme='README.md',tags='PSModule source-built',projectUrl=gold['source_repository']).items(): E.SubElement(meta,name).text=value
E.SubElement(meta,'license',type='expression').text='MIT'
E.SubElement(meta,'repository',type='git',url=gold['source_repository'],commit=gold['source_commit'])
E.SubElement(E.SubElement(meta,'dependencies'),'dependency',id='PackageManagement',version='[1.4.4,)')
E.indent(root)
assets['PowerShellGet.nuspec']=E.tostring(root,encoding='utf-8',xml_declaration=True)
assets['LICENSE']=(prepared/'LICENSE').read_bytes()
assets['README.md']=(here/'README.md').read_bytes()
assets['source-build/provenance.json']=(prepared/'source-build.json').read_bytes()
types=E.Element('Types',xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
E.SubElement(types,'Default',Extension='rels',ContentType='application/vnd.openxmlformats-package.relationships+xml')
for extension in sorted({Path(name).suffix.removeprefix('.') for name in assets if Path(name).suffix}):
    E.SubElement(types,'Default',Extension=extension,ContentType='application/octet')
E.SubElement(types,'Override',PartName='/LICENSE',ContentType='text/plain')
assets['[Content_Types].xml']=E.tostring(types,encoding='utf-8',xml_declaration=True)
assets['_rels/.rels']=b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.microsoft.com/packaging/2010/07/manifest" Target="/PowerShellGet.nuspec" Id="R1"/></Relationships>'
output.mkdir()
target=output/'powershellget.2.2.5.nupkg'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(assets.items()):
        item=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
        item.external_attr=0o100644<<16;z.writestr(item,data)
print('PASS all16 source/published module assets and complete source-only package:',target)
