"""Preserve original NuGet Core projects and all production C# for .NET8 source build."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:])
gold=json.loads(Path(__file__).with_name('source-inventory.json').read_text())
sha=lambda data:hashlib.sha256(data).hexdigest()
for name,record in gold['projects'].items():
    folder=source/'src/NuGet.Core'/name
    assert sha((folder/(name+'.csproj')).read_bytes())==record['original_project_sha256']
    actual={p.relative_to(source).as_posix():sha(p.read_bytes()) for p in folder.rglob('*.cs')}
    assert actual==record['original_cs'],name
    for path,digest in record['original_resx'].items():assert sha((source/path).read_bytes())==digest,path
    for path,digest in record.get('original_embedded',{}).items():assert sha((source/path).read_bytes())==digest,path
for path,digest in gold['shared_cs'].items():assert sha((source/path).read_bytes())==digest,path
shutil.copytree(source,out)
# Select the existing source .NET8 ProtectedData implementation in the original
# central package declarations. Other source-build version substitutions are
# supplied by the upstream DotNetPackageVersionPropsPath mechanism.
path=out/'Directory.Packages.props';tree=E.parse(path)
items=[item for item in tree.iter('PackageVersion') if item.get('Include')=='System.Security.Cryptography.ProtectedData']
assert len(items)==1 and items[0].get('Version')=='4.4.0'
items[0].set('Version','8.0.0');E.indent(tree);tree.write(path,encoding='utf-8',xml_declaration=True)
for path in out.rglob('*'):
    if path.is_file() and path.suffix.lower() in ('.dll','.exe','.pdb','.nupkg'):
        path.unlink()
# The source archive uses LF while the published Windows build uses CRLF in
# multiline messages. Encode Windows message newlines as XML character refs so
# the SDK's normalizing XML reader preserves the original published values.
resource_overlays={}
for name,record in gold['projects'].items():
    for relative in record['original_resx']:
        path=out/relative;data=path.read_bytes();encoding='utf-8-sig' if data.startswith(b'\xef\xbb\xbf') else 'utf-8'
        text=data.decode(encoding)
        updated=re.sub(r'(<value(?:\s[^>]*)?>)(.*?)(</value>)',
                       lambda m:m[1]+m[2].replace('\r\n','\n').replace('\n','&#xD;&#xA;')+m[3],text,flags=re.S)
        if updated!=text:
            path.write_bytes(updated.encode(encoding))
            resource_overlays[relative]=dict(original_sha256=sha(data),prepared_sha256=sha(path.read_bytes()),
                                           change='XML character refs preserve published Windows CRLF inside multiline resource values')
(out/'source-resource-overlays.json').write_text(json.dumps(resource_overlays,indent=2)+'\n')
# Observe the actual compiler and resolver inputs after the original project
# conditions/imports have run. Do not replace any upstream Compile items.
capture=Path(__file__).with_name('SourceInputs.targets')
shutil.copy2(capture,out/capture.name)
path=out/'Directory.Build.targets';original=path.read_bytes()
text=original.decode('utf-8-sig')
assert text.count('</Project>')==1
text=text.replace('</Project>','  <Import Project="SourceInputs.targets" />\n</Project>')
path.write_text(text,encoding='utf-8')
metadata_overlays={}
for relative in ['Directory.Packages.props','Directory.Build.targets']:
    metadata_overlays[relative]=dict(original_sha256=sha((source/relative).read_bytes()),
                                   prepared_sha256=sha((out/relative).read_bytes()))
metadata_overlays[capture.name]=dict(owned_sha256=sha(capture.read_bytes()))
(out/'source-metadata-overlays.json').write_text(json.dumps(metadata_overlays,indent=2)+'\n')
(out/'source-build-inventory.json').write_text(json.dumps(gold,indent=2)+'\n')
print('PASS complete original NuGet Core source/resource inventory and central ProtectedData source version selection')
