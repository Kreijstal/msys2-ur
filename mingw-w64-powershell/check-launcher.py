"""Exercise the actual native launcher using Windows argument serialization."""
from pathlib import Path
import argparse
import json
import os
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('prefix',type=Path)
parser.add_argument('output',type=Path)
parser.add_argument('--dotnet-root',type=Path,required=True)
args=parser.parse_args();prefix=args.prefix.resolve();out=args.output.resolve();out.mkdir()
exe=prefix/'bin/pwsh.exe';app=prefix/'lib/powershell/7'
probe=out/'argument probe λ.ps1'
probe.write_text('''param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Values)
$ErrorActionPreference='Stop'
[ordered]@{values=@($Values);home=$PSHOME;engine=[System.Management.Automation.PowerShell].Assembly.Location;runtime=[Environment]::Version.ToString();dotnet=$env:DOTNET_ROOT;dotnet64=$env:DOTNET_ROOT_X64;path=$env:PATH} | ConvertTo-Json -Compress
''',encoding='utf-8')
env=dict(os.environ,DOTNET_ROOT=str(args.dotnet_root.resolve()),DOTNET_ROOT_X64=str(args.dotnet_root.resolve()),POWERSHELL_TELEMETRY_OPTOUT='1',DOTNET_CLI_TELEMETRY_OPTOUT='1')
# Force the installed launcher to select its own source root over a foreign one.
if (prefix/'lib/dotnet/shared/Microsoft.NETCore.App/8.0.31/System.Private.CoreLib.dll').is_file():
 env['DOTNET_ROOT']=str(out/'foreign runtime');env['DOTNET_ROOT_X64']=env['DOTNET_ROOT']
expected=['λ spaces','quote"inside','C:\\trailing\\','', '日本語','two \\"quoted\\" words']
before=dict(os.environ)
command=[str(exe),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(probe),*expected]
result=subprocess.run(command,env=env,text=True,encoding='utf-8',capture_output=True,timeout=90)
assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
actual=json.loads(result.stdout);assert actual['values']==expected,(actual['values'],expected)
(out/'actual.json').write_text(json.dumps(actual,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert Path(actual['home']).resolve()==app
assert Path(actual['engine']).resolve()==app/'System.Management.Automation.dll'
assert actual['runtime']=='8.0.31'
assert Path(actual['dotnet']).resolve()==args.dotnet_root.resolve()
assert Path(actual['dotnet64']).resolve()==args.dotnet_root.resolve()
# The unchanged original ConsoleHost prepends PSHOME on entry.
parts=[Path(p).resolve() for p in actual['path'].split(';')[:3] if p]
assert parts[:2]==[app,exe.parent],(parts,app,exe.parent)
assert args.dotnet_root.resolve().parent.parent/'bin' in parts
exit_result=subprocess.run([str(exe),'-NoLogo','-NoProfile','-NonInteractive','-Command','exit 37'],env=env,capture_output=True,timeout=45)
assert exit_result.returncode==37,exit_result.returncode
assert dict(os.environ)==before
(out/'results.json').write_text(json.dumps(dict(arguments=actual,child_exit_code=37,parent_environment_unchanged=True),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS native launcher Unicode/quotes/empty/trailing-backslash arguments, source engine/runtime/root, process-only environment and exact child exit status')
