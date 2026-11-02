"""Force the original CompileAsn target and compare every generated source."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as E

root=Path(sys.argv[1]).resolve();out=root/'asn-build2';out.mkdir()
model=json.loads((root/'plan/evaluated.json').read_text())['System.Security.Cryptography.Pkcs']
source=root/'r';inputs=list(dict.fromkeys(Path(item['full_path']).resolve() for item in model['items']['AsnXml']))
assert inputs and all(p.is_file() and p.is_relative_to(source) for p in inputs)
original={p:Path(str(p)+'.cs').read_bytes() for p in inputs}
for p in inputs:Path(str(p)+'.cs').unlink()
# Import the evaluated original project and its unchanged CompileAsn target.
project=E.Element('Project');E.SubElement(project,'Import',Project=(root/'plan/Evaluate.csproj').as_posix())
pg=E.SubElement(project,'PropertyGroup');E.SubElement(pg,'IntermediateOutputPath').text=out.as_posix()+'/'
path=out/'Generate.proj';E.ElementTree(project).write(path,encoding='utf-8',xml_declaration=True)
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
command=[prefix/'lib/dotnet/dotnet.exe','msbuild',path,'-t:CompileAsn','-nologo','-v:minimal']
with (out/'generate.log').open('w',encoding='utf-8') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
if result.returncode!=0:
    for p,expected in original.items():Path(str(p)+'.cs').write_bytes(expected)
    raise AssertionError(result.returncode)
records={}
for p,expected in original.items():
    generated=Path(str(p)+'.cs');actual=generated.read_bytes()
    assert actual.decode('utf-8-sig').replace('\r\n','\n')==expected.decode('utf-8-sig').replace('\r\n','\n'),p
    # Retain the repository's byte formatting after proving all generated text.
    if actual!=expected:
        newline=b'\r\n' if b'\r\n' in expected else b'\n'
        normalized=actual.decode('utf-8-sig').replace('\r\n','\n').encode('utf-8').replace(b'\n',newline)
        if expected.startswith(b'\xef\xbb\xbf'):normalized=b'\xef\xbb\xbf'+normalized
        assert normalized==expected,p
        generated.write_bytes(normalized)
    records[p.relative_to(source).as_posix()]=dict(xml_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),original_generated_sha256=hashlib.sha256(expected).hexdigest(),raw_generated_sha256=hashlib.sha256(actual).hexdigest(),final_generated_sha256=hashlib.sha256(generated.read_bytes()).hexdigest(),formatting_normalized=actual!=expected)
(out/'results.json').write_text(json.dumps(dict(command=[str(x) for x in command],exit_code=0,generated_models=len(records),all_original_generated_source_text_equal=True,inputs=records,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS',len(records),'ASN models regenerated with original targets/XSLT;all original generated source text matches')
