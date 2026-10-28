"""Package the source binary in the original root PSModule layout."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as E
import zipfile

prepared,output=(Path(p).resolve() for p in sys.argv[1:])
output.mkdir()
here=Path(__file__).resolve().parent
module=prepared/'module';module.mkdir()
shutil.copyfile(prepared/'bin/Release/net8.0/Microsoft.PowerShell.ThreadJob.dll',module/'Microsoft.PowerShell.ThreadJob.dll')
shutil.copyfile(prepared/'ThreadJob.psd1',module/'ThreadJob.psd1')
record=json.loads((prepared/'source-inventory.json').read_text())
record['source_archive_sha256']='af57cfa480c67e7f23e583fd190964db560d35263b3c021ce621a77eef2e9c8c'
record['module_files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(module.iterdir())}
(prepared/'source-build.json').write_text(json.dumps(record,indent=2)+'\n')
root=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd')
meta=E.SubElement(root,'metadata')
for name,value in dict(id='ThreadJob',version='2.0.3',authors='Microsoft Corporation',
    description='Complete source ThreadJob module for source PowerShell7.4 on.NET8, with debugger overload adaptation.',
    requireLicenseAcceptance='false',readme='README.md',tags='PSModule source-built',
    projectUrl='https://github.com/PaulHigin/PSThreadJob').items():E.SubElement(meta,name).text=value
E.SubElement(meta,'license',type='expression').text='MIT'
E.SubElement(meta,'repository',type='git',url='https://github.com/PaulHigin/PSThreadJob',commit=record['source_commit'])
E.indent(root)
assets={p.name:p.read_bytes() for p in module.iterdir()}
assets['ThreadJob.nuspec']=E.tostring(root,encoding='utf-8',xml_declaration=True)
assets['LICENSE']=(prepared/'LICENSE').read_bytes()
assets['README.md']=(here/'README.md').read_bytes()
assets['source-build/provenance.json']=(prepared/'source-build.json').read_bytes()
assets['[Content_Types].xml']=b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="dll" ContentType="application/octet-stream"/><Default Extension="psd1" ContentType="text/plain"/><Default Extension="nuspec" ContentType="application/octet"/><Default Extension="md" ContentType="text/plain"/><Default Extension="json" ContentType="application/json"/></Types>'
assets['_rels/.rels']=b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.microsoft.com/packaging/2010/07/manifest" Target="/ThreadJob.nuspec" Id="R1"/></Relationships>'
with zipfile.ZipFile(output/'threadjob.2.0.3.nupkg','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(assets.items()):
        item=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
        item.external_attr=0o100644<<16;z.writestr(item,data)
print('Packed source ThreadJob2.0.3: sole owned binary, original manifest and license')
