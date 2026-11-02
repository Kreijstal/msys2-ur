"""Owned offline module packages; no gallery or executable bootstrap is needed."""
from pathlib import Path
import sys
import xml.etree.ElementTree as E
import zipfile

out = Path(sys.argv[1]); out.mkdir()
feed = out/'feed'; feed.mkdir()
for name, version in [('Owned.Dependency','1.0.0'),('Owned.Module','1.0.0'),('Owned.Module','1.1.0')]:
    root=E.Element('package'); meta=E.SubElement(root,'metadata')
    for key,value in dict(id=name,version=version,authors='Owned fixture',description='Offline module fixture',tags='PSModule OwnedFixture',requireLicenseAcceptance='false').items():
        E.SubElement(meta,key).text=value
    dependency=""
    if name=='Owned.Module':
        E.SubElement(E.SubElement(meta,'dependencies'),'dependency',id='Owned.Dependency',version='[1.0.0]')
        dependency="RequiredModules = @(@{ModuleName='Owned.Dependency';RequiredVersion='1.0.0'})\n"
    function='Get-OwnedDependencyValue' if name=='Owned.Dependency' else 'Get-OwnedValue'
    manifest=f"@{{\nRootModule='{name}.psm1'\nModuleVersion='{version}'\nGUID='1d2a8fb7-6153-495f-863d-81be7bfa17bb'\nAuthor='Owned fixture'\nDescription='Offline module fixture'\n{dependency}FunctionsToExport=@('{function}')\nCmdletsToExport=@()\nAliasesToExport=@()\n}}\n"
    assets={f'{name}.nuspec':E.tostring(root),f'{name}.psd1':manifest.encode(),f'{name}.psm1':f"function {function} {{ '{name} {version} λ owned' }}\nExport-ModuleMember -Function {function}\n".encode()}
    with zipfile.ZipFile(feed/f'{name}.{version}.nupkg','w',zipfile.ZIP_DEFLATED) as z:
        for key,value in assets.items(): z.writestr(key,value)
for version in ['1.0.0','1.1.0']:
    name='Owned.Script'
    root=E.Element('package'); meta=E.SubElement(root,'metadata')
    for key,value in dict(id=name,version=version,authors='Owned fixture',description='Offline script fixture',tags='PSScript OwnedFixture',requireLicenseAcceptance='false').items():
        E.SubElement(meta,key).text=value
    script=f'''\n<#PSScriptInfo

.VERSION {version}

.GUID 5465e6ea-de3c-4b63-b1f0-a2a5761b92c4

.AUTHOR Owned fixture

.COMPANYNAME Owned fixture

.COPYRIGHT Owned fixture

.TAGS OwnedFixture

#>

<#

.DESCRIPTION
Offline script fixture

#>
param()
'Owned.Script {version} λ owned'
'''
    with zipfile.ZipFile(feed/f'{name}.{version}.nupkg','w',zipfile.ZIP_DEFLATED) as z:
        z.writestr(f'{name}.nuspec',E.tostring(root));z.writestr(f'{name}.ps1',script.encode())
    (out/f'script-{version}.expected.ps1').write_bytes(script.encode())
print('PASS owned offline module feed created')
