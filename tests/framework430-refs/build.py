"""Build all original profiles of eight reference-only legacy NuGet packages."""
from pathlib import Path
import hashlib
import json
import re
import runpy
import subprocess
import sys
import tarfile

sbrp, corefx, out, prefix, compiler = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here = Path(__file__).parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(sbrp) == '2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79'
assert sha(corefx) == '986a512c70d55ed7a1ed8cbb9d8323017c9cc83e77e95e833c7b91f42e4ef601'
matrix = json.loads((here / 'inputs/source-contract-build-matrix.json').read_text())
profiles = json.loads((here / 'inputs/baselines1/profiles.json').read_text())
resources = json.loads((here / 'inputs/reference-data.json').read_text())
commands = []; records = {}; original_hashes = {}
def run(label, command):
    command = [str(p) for p in command]; result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / (label + '.log')).write_bytes(result.stdout); commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, (label, result.stdout.decode('utf-8', errors='replace')[-6000:])
def extract(tar, entries, name, kind):
    data = tar.extractfile(entries[name]).read(); path = out / 'source' / kind / name
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); original_hashes[kind + '/' + name] = hashlib.sha256(data).hexdigest(); return path
with tarfile.open(sbrp) as st, tarfile.open(corefx) as ct:
    assert st.pax_headers['comment'] == '5aeee2738338530a92d7f6caa2c7d5f569fed3c4'
    assert ct.pax_headers['comment'] == '9688ddbb62c04189cac4c4a06e31e93377dccd41'
    se = {m.name.partition('/')[2]: m for m in st if m.isfile()}; ce = {m.name.partition('/')[2]: m for m in ct if m.isfile()}
    for name in ['LICENSE.txt']: extract(st, se, name, 'sbrp')
    for name in ['LICENSE', 'THIRD-PARTY-NOTICES']: extract(ct, ce, name, 'corefx')
    for label, row in profiles.items():
        name, tfm = row['name'], row['framework']; baseline = json.loads((here / 'inputs' / (label + '.json')).read_text())[name + '.dll']
        raw = extract(st, se, 'src/referencePackages/src/' + name.lower() + '/4.3.0/ref/' + tfm + '/' + name + '.cs', 'sbrp')
        folder = out / 'raw' / name / tfm; folder.mkdir(parents=True); sources = [raw]
        if name in ['System.Diagnostics.Debug', 'System.Diagnostics.Tools']:
            original = extract(ct, ce, 'src/' + name + '/ref/' + name + '.cs', 'corefx')
            if name == 'System.Diagnostics.Debug' and tfm == 'netstandard1.0':
                projection = folder / 'Debug.Ported.cs'; projection.write_text(runpy.run_path(str(here / 'port-debug.py'))['port'](raw.read_text(encoding='utf-8-sig'), original.read_text(encoding='utf-8-sig'))); sources = [projection]
            else:
                text = raw.read_text(encoding='utf-8-sig'); marker = 'namespace System.Diagnostics' if name == 'System.Diagnostics.Debug' else 'namespace System.CodeDom.Compiler'
                info = folder / 'AssemblyInfo.cs'; info.write_text(text[:text.index(marker)]); sources = [original, info]
        closure = set()
        def select(ident):
            if ident in closure: return
            assert ident in matrix, ident
            closure.add(ident)
            for ref in matrix[ident]['references']:
                n, v = ref.split(', Version='); select(n + '/' + v.split(',')[0])
        for ref in baseline['references']:
            n, v = ref.split(', Version='); select(n + '/' + v.split(',')[0])
        chosen = {}
        for ident in sorted(closure):
            n, version = ident.split('/')
            if n not in chosen or tuple(map(int, version.split('.'))) > tuple(map(int, chosen[n].split('/')[1].split('.'))): chosen[n] = ident
        refs = [prefix / 'lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts' / ident / (ident.split('/')[0] + '.dll') for ident in chosen.values()]
        assert all(p.is_file() for p in refs)
        v = next(r['native_version'] for r in resources if r['name'] == name and '/' + tfm + '/' in r['file']); language = 1033 if v['Language'] == 'English (United States)' else 0
        assert v['Language'] in ['English (United States)', 'Language Neutral']
        rc = ['LANGUAGE 9,1' if language else 'LANGUAGE 0,0', '1 VERSIONINFO', 'FILEVERSION ' + ','.join(re.findall(r'\d+', v['FileVersion'])[:4]), 'PRODUCTVERSION ' + ','.join(re.findall(r'\d+', v['ProductVersion'])[:4]), 'FILEFLAGSMASK 0x3f', 'FILEFLAGS 0', 'FILEOS 4', 'FILETYPE 2', 'FILESUBTYPE 0', 'BEGIN', 'BLOCK "StringFileInfo"', 'BEGIN', 'BLOCK "040904b0"' if language else 'BLOCK "000004b0"', 'BEGIN']
        for field in ['CompanyName','FileDescription','FileVersion','InternalName','LegalCopyright','LegalTrademarks','OriginalFilename','ProductName','ProductVersion']: rc.append('VALUE ' + json.dumps(field) + ', L' + json.dumps(v[field], ensure_ascii=True).replace('\\u','\\x'))
        rc += ['END','END','BLOCK "VarFileInfo"','BEGIN','VALUE "Translation", ' + str(language) + ', 1200','END','END']
        (folder / 'version.rc').write_text('\n'.join(rc) + '\n'); run(label + '-rc', [prefix / 'bin/llvm-rc.exe', '-fo', folder / 'version.res', folder / 'version.rc'])
        args = ['/nostdlib+','/target:library','/refonly','/unsafe+','/nullable:disable','/langversion:latest','/optimize+','/deterministic+','/warnaserror+','/nowarn:1701,1702','/publicsign+','/keyfile:"' + (here / 'inputs/Microsoft.snk').as_posix() + '"','/out:"' + (folder / (name + '.dll')).as_posix() + '"','/win32res:"' + (folder / 'version.res').as_posix() + '"','/runtimeMetadataVersion:v4.0.30319']
        args += ['/reference:"' + p.as_posix() + '"' for p in refs] + ['"' + p.as_posix() + '"' for p in sources]
        rsp = folder / 'compile.rsp'; rsp.write_text('\n'.join(args) + '\n'); run(label, [prefix / 'lib/dotnet/dotnet.exe', compiler / 'csc.dll', '-noconfig', '@' + str(rsp)])
        records[label] = dict(source_compiler_input_sha256={p.as_posix():sha(p) for p in sources}, reference_sha256={p.as_posix():sha(p) for p in refs}, original_framework=tfm)
        print('PASS original source reference compilation:', label, flush=True)
(out / 'results.json').write_text(json.dumps(dict(commands=commands, profiles=records, original_source_sha256=original_hashes, original_files_edited_in_place=0, Debug_NS10_Conditional_attribute_source_port=True, original_Debug_NS13_and_Tools_source_used=True, runtime_implementations_supplied=False, full_dependency_goal_complete=False), indent=2) + '\n')
