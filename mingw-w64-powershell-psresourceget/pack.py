"""Package the complete source module, private libraries and compiler provenance."""
from pathlib import Path
import sys, xml.etree.ElementTree as E, zipfile

module,out=(Path(p) for p in sys.argv[1:]);out.mkdir()
name='Microsoft.PowerShell.PSResourceGet'
root=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');meta=E.SubElement(root,'metadata')
for key,value in dict(id=name,version='1.1.1',authors='Microsoft Corporation',description='Complete original PSResourceGet module retargeted to source.NET8 and source PowerShell7.4, with source-built private dependencies.',requireLicenseAcceptance='false',readme='README.md',tags='PSModule source-built',projectUrl='https://github.com/PowerShell/PSResourceGet').items():E.SubElement(meta,key).text=value
E.SubElement(meta,'license',type='expression').text='MIT'
E.SubElement(meta,'repository',type='git',url='https://github.com/PowerShell/PSResourceGet',commit='44697aed1740126153a8d9dd0ef368261b2fe45c')
E.indent(root)
assets={p.relative_to(module).as_posix():p.read_bytes() for p in module.rglob('*') if p.is_file()}
assets[name+'.nuspec']=E.tostring(root,encoding='utf-8',xml_declaration=True)
types=E.Element('Types',xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
for suffix in sorted({Path(p).suffix[1:] for p in assets}):E.SubElement(types,'Default',Extension=suffix,ContentType='application/octet-stream')
E.SubElement(types,'Default',Extension='rels',ContentType='application/vnd.openxmlformats-package.relationships+xml')
assets['[Content_Types].xml']=E.tostring(types,encoding='utf-8',xml_declaration=True)
assets['_rels/.rels']=b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.microsoft.com/packaging/2010/07/manifest" Target="/Microsoft.PowerShell.PSResourceGet.nuspec" Id="R1"/></Relationships>'
with zipfile.ZipFile(out/(name.lower()+'.1.1.1.nupkg'),'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path,data in sorted(assets.items()):
        item=zipfile.ZipInfo(path,date_time=(1980,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o100644<<16;z.writestr(item,data)
print('PASS PSResourceGet PSModule package: full original module, private source dependencies/licenses, reference/XML and source/compiler provenance')
