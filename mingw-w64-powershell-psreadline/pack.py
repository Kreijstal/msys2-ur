"""Create a source PSModule NuGet with the complete Core module layout."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as E
import zipfile

prepared,output=(Path(p).resolve() for p in sys.argv[1:])
output.mkdir();module=prepared/'module';module.mkdir()
here=Path(__file__).resolve().parent
record=json.loads((prepared/'source-inventory.json').read_text())
golden=json.loads((here/'published-provenance.json').read_text())
for path in golden['original_module_assets']:
    source=prepared/path
    assert hashlib.sha256(source.read_bytes()).hexdigest()==golden['original_module_assets'][path]
    shutil.copyfile(source,module/source.name)
for name in ('Microsoft.PowerShell.PSReadLine2.dll','Microsoft.PowerShell.Pager.dll'):
    shutil.copyfile(prepared/'PSReadLine/bin/Release/net8.0'/name,module/name)
(module/'net6plus').mkdir()
shutil.copyfile(prepared/'Polyfill/bin/Release/net8.0/Microsoft.PowerShell.PSReadLine.Polyfiller.dll',module/'net6plus/Microsoft.PowerShell.PSReadLine.Polyfiller.dll')
record['source_archive_sha256']=golden['source_archive_sha256']
record['module_files']={p.relative_to(module).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(module.rglob('*')) if p.is_file()}
record['bundled_pager_source_package']='Microsoft.PowerShell.Pager/1.0.0'
(prepared/'source-build.json').write_text(json.dumps(record,indent=2)+'\n')
root=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');meta=E.SubElement(root,'metadata')
for name,value in dict(id='PSReadLine',version='2.3.6',authors='Microsoft Corporation',
    description='Complete source PSReadLine Core module for source PowerShell7.4 on.NET8, including source Pager and original Core type forwarders.',
    requireLicenseAcceptance='false',readme='README.md',tags='PSModule source-built',
    projectUrl='https://github.com/PowerShell/PSReadLine').items():E.SubElement(meta,name).text=value
E.SubElement(meta,'license',type='expression').text='MIT'
E.SubElement(meta,'repository',type='git',url='https://github.com/PowerShell/PSReadLine',commit=record['source_commit'])
E.indent(root)
assets={p.relative_to(module).as_posix():p.read_bytes() for p in module.rglob('*') if p.is_file()}
assets['PSReadLine.nuspec']=E.tostring(root,encoding='utf-8',xml_declaration=True)
assets['README.md']=(here/'README.md').read_bytes()
assets['source-build/provenance.json']=(prepared/'source-build.json').read_bytes()
assets['[Content_Types].xml']=b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="dll" ContentType="application/octet-stream"/><Default Extension="psd1" ContentType="text/plain"/><Default Extension="psm1" ContentType="text/plain"/><Default Extension="ps1xml" ContentType="text/plain"/><Default Extension="ps1" ContentType="text/plain"/><Default Extension="nuspec" ContentType="application/octet"/><Default Extension="md" ContentType="text/plain"/><Default Extension="txt" ContentType="text/plain"/><Default Extension="json" ContentType="application/json"/></Types>'
assets['_rels/.rels']=b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.microsoft.com/packaging/2010/07/manifest" Target="/PSReadLine.nuspec" Id="R1"/></Relationships>'
with zipfile.ZipFile(output/'psreadline.2.3.6.nupkg','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(assets.items()):
        item=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
        item.external_attr=0o100644<<16;z.writestr(item,data)
print('Packed complete source PSReadLine Core layout:',len(record['module_files']),'module files')
