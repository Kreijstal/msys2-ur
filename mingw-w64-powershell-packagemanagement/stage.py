"""Stage the original Core module layout with all six rebuilt source assemblies."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

prepared,output=(Path(p).resolve() for p in sys.argv[1:])
output.mkdir();source=prepared/'oneget/src'
for name in ('PackageManagement.psd1','PackageManagement.psm1','PackageManagement.Resources.psd1','PackageProviderFunctions.psm1','PackageManagement.format.ps1xml'):
    shutil.copyfile(source/'Microsoft.PowerShell.PackageManagement'/name,output/name)
dsc=output/'DSCResources';dsc.mkdir()
dscsource=source/'Microsoft.PackageManagement.DscResources'
for name in ('PackageManagementDscUtilities.psm1','PackageManagementDscUtilities.strings.psd1'):
    shutil.copyfile(dscsource/name,dsc/name)
for name in ('MSFT_PackageManagement','MSFT_PackageManagementSource'):
    shutil.copytree(dscsource/name,dsc/name)
target=output/'coreclr/netstandard2.0';target.mkdir(parents=True)
record=json.loads((prepared/'source-inventory.json').read_text())
for name in record['projects']:
    shutil.copyfile(source/name/'bin/Debug/net8.0'/(name+'.dll'),target/(name+'.dll'))
record['build_configuration']='Debug: matches all six published DebuggableAttribute flags263 and the original DEBUG-only ToString public method'
record['module_files']={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
(prepared/'staged-module.json').write_text(json.dumps(record,indent=2)+'\n')
print('Staged original Core module/scripts/DSC and all six rebuilt production assemblies')
