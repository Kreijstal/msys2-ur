"""Apply the original generator configuration import to existing private wrappers."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as E

out=Path(sys.argv[1]).resolve();root=out.parent
record=json.loads((out/'source-inputs.json').read_text())
source=out/'runtime-source'
props=source/'src/libraries/System.Runtime.InteropServices/gen/LibraryImportGenerator/Microsoft.Interop.LibraryImportGenerator.props'
native=subprocess.check_output(['cygpath','-am',str(props)],text=True).strip()
for name in record['order']:
    project=out/'libraries'/name/'Build.csproj';tree=E.parse(project)
    for path,digest in record['projects'][name]['original_cs'].items():assert hashlib.sha256((source/path).read_bytes()).hexdigest()==digest,(name,path)
    if not any(e.get('Project')==native for e in tree.iter('Import')):
        for group in tree.findall('ItemGroup'):
            for e in list(group):
                if e.tag=='CompilerVisibleProperty' and e.get('Include')=='LibraryImportGenerator_UseMarshalType':group.remove(e)
        E.SubElement(tree.getroot(),'Import',Project=native)
        E.indent(tree);tree.write(project,encoding='utf-8',xml_declaration=True)
record['generator_configuration_props_sha256']=hashlib.sha256(props.read_bytes()).hexdigest()
(out/'source-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS original generator configuration props and unchanged production source hashes')
