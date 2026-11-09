"""Extract native table declarations from Clang's AST; discard the full AST."""
from pathlib import Path
import subprocess,sys,json,hashlib
prefix=Path(sys.argv[1]);out=Path(sys.argv[2]);header=prefix/'include/mi.h'
source=out/'header.c';source.write_text('#include <mi.h>\n')
result=subprocess.run([str(prefix/'bin/clang'),'-Xclang','-ast-dump=json','-fsyntax-only','-x','c',str(source)],text=True,capture_output=True,check=True)
records={}
def visit(n):
    if n.get('kind')=='RecordDecl' and n.get('completeDefinition') and n.get('name','').endswith('FT'):
        records[n['name']]={'fields':[{'name':v['name'],'type':v.get('type')} for v in n.get('inner',[]) if v.get('kind')=='FieldDecl']}
    for value in n.get('inner',[]):visit(value)
visit(json.loads(result.stdout))
record={'header':str(header),'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'header_owner':subprocess.check_output(['pacman','-Qo',str(header)],text=True).strip(),'compiler':subprocess.check_output([str(prefix/'bin/clang'),'--version'],text=True).splitlines()[0],'records':records}
(out/'native-schema.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS native table schema',len(records),prefix)
