"""Create the source-only PSModule NuGet package with deterministic ZIP metadata."""
from pathlib import Path
import sys
import xml.etree.ElementTree as E
import zipfile

prepared, output = (Path(p).resolve() for p in sys.argv[1:])
output.mkdir()
here=Path(__file__).resolve().parent
ns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd'
root=E.Element('package',xmlns=ns);meta=E.SubElement(root,'metadata')
for name,value in dict(id='Microsoft.PowerShell.Archive',version='1.2.6',authors='Microsoft Corporation',
    description='Source-built PowerShell ZIP archive module, with fallback warning resource correction.',
    requireLicenseAcceptance='false',readme='README.md',tags='PSModule source-built',
    projectUrl='https://github.com/PowerShell/Microsoft.PowerShell.Archive').items():E.SubElement(meta,name).text=value
E.SubElement(meta,'license',type='expression').text='MIT'
E.SubElement(meta,'repository',type='git',url='https://github.com/PowerShell/Microsoft.PowerShell.Archive',commit='87428e309898a728fb0287eab31b5cd214ceb9ba')
E.indent(root)
assets={p.relative_to(prepared/'module').as_posix():p.read_bytes() for p in (prepared/'module').rglob('*') if p.is_file()}
assets['Microsoft.PowerShell.Archive.nuspec']=E.tostring(root,encoding='utf-8',xml_declaration=True)
assets['LICENSE']=(prepared/'LICENSE').read_bytes()
assets['README.md']=(here/'README.md').read_bytes()
assets['source-build/provenance.json']=(prepared/'source-build.json').read_bytes()
assets['[Content_Types].xml']=b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="psd1" ContentType="text/plain"/><Default Extension="psm1" ContentType="text/plain"/><Default Extension="nuspec" ContentType="application/octet"/><Default Extension="md" ContentType="text/plain"/><Default Extension="json" ContentType="application/json"/></Types>'
assets['_rels/.rels']=b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.microsoft.com/packaging/2010/07/manifest" Target="/Microsoft.PowerShell.Archive.nuspec" Id="R1"/></Relationships>'
target=output/'microsoft.powershell.archive.1.2.6.nupkg'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(assets.items()):
        item=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
        item.external_attr=0o100644<<16;z.writestr(item,data)
print('Packed source-only PSModule1.2.6:',target)
