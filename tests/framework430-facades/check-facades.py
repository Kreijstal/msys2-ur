"""Compare complete facade APIs, identities, scopes, resources and exported records."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

producer, out, tools, prefix = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists(); out.mkdir(); here=Path(__file__).parent; dotnet=prefix/'lib/dotnet/dotnet.exe'
profiles={n:r for n,r in json.loads((here/'inputs/profiles.json').read_text()).items() if not r['reference_source']};files=[producer/'ref'/r['name']/r['framework']/(r['name']+'.dll') for r in profiles.values()];commands=[]
def run(label,command):
    command=[str(p) for p in command];r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(label+'.log')).write_bytes(r.stdout);commands.append(dict(command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.stdout.decode(errors='replace')[-6000:]);return r
run('metadata',[dotnet,tools/'inspector/bin/Release/net8.0/Inspect.dll',out/'metadata.json',*files])
run('exports',[dotnet,tools/'forwarders/bin/Release/net8.0/Forwarders.dll',out/'exports.json',*files])
resources=json.loads(run('resources',[dotnet,tools/'resources/bin/Release/net8.0/ReadResources.dll',*files]).stdout)
metadata=json.loads((out/'metadata.json').read_text());exports=json.loads((out/'exports.json').read_text());wanted_resources=json.loads((here/'inputs/reference-data.json').read_text());records={};differences={};canon=lambda rows:sorted(json.dumps(r,sort_keys=True) for r in rows)
for label,row in profiles.items():
    name,tfm=row['name'],row['framework'];dll=producer/'ref'/name/tfm/(name+'.dll');actual=metadata[name+'.dll'];wanted=json.loads((here/'inputs'/(label+'.json')).read_text())[name+'.dll'];diff={}
    for key in ['identity','api']:
        if actual[key]!=wanted[key]:diff[key]=dict(actual=actual[key],expected=wanted[key])
    if set(actual['references'])!=set(wanted['references']):diff['assembly_references']=dict(actual=actual['references'],expected=wanted['references'])
    if canon(actual['attributes'])!=canon(wanted['attributes']):diff['assembly_attributes']=dict(actual=actual['attributes'],expected=wanted['attributes'])
    native=next(r for r in resources if r['name']==name);expected=next(r for r in wanted_resources if r['name']==name and '/'+tfm+'/' in r['file'])
    for key in ['name','version','public_key','public_key_token','attributes','resources','embedded_nonresource_blob_hashes','exported_types','native_version','references']:
        if native[key]!=expected[key]:diff['resource_'+key]=dict(actual=native[key],expected=expected[key])
    forward=next(r for r in exports if r['identity'].startswith(name+','));expected_forward=json.loads((here/'inputs/baselines1'/(label+'-exports.json')).read_text())[0]
    for key in ['identity','reference_only','assembly_references','exported_types']:
        if forward[key]!=expected_forward[key]:diff['forward_'+key]=dict(actual=forward[key],expected=expected_forward[key])
    if diff:differences[label]=diff
    records[label]=dict(identity=actual['identity'],owned_API_entries=len(actual['api']),original_exported_types=len(expected_forward['exported_types']),source_resource_strings=sum(len(v) for v in expected['resources'].values()),DLL_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),all_original_metadata_verified=not diff)
    print('PASS' if not diff else 'DIFFERENCES',label,'fields',list(diff),flush=True)
(out/'differences.json').write_text(json.dumps(differences,indent=2)+'\n')
assert not differences, str(out/'differences.json')
(out/'results.json').write_text(json.dumps(dict(commands=commands,facades=records,all_7_original_facades_metadata_verified=True,original_owned_API_entries=sum(v['owned_API_entries'] for v in records.values()),original_exported_types=sum(v['original_exported_types'] for v in records.values()),original_source_resource_strings=sum(v['source_resource_strings'] for v in records.values()),runtime_execution_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
