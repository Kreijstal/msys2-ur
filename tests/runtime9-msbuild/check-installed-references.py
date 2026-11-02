"""Validate installed source NET9 contracts with fresh metadata and API consumers."""
from pathlib import Path
import os,shutil,subprocess,sys
root,prepared,out,validator=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir()
for name in ['build-status.json','evaluated.json','source-projects.json','projects.json','NuGet.config']:shutil.copyfile(prepared/name,out/name)
for name in ['keys','stubs']:shutil.copytree(prepared/name,out/name)
refs=Path('/clang64/lib/dotnet/reference-packs/runtime-9.0.11/ref/net9.0');assert len(list(refs.glob('*.dll')))==164
(out/'ref').mkdir();shutil.copytree(refs,out/'ref/net9.0')
for p in refs.glob('*.dll'):assert p.read_bytes()==(prepared/'ref/net9.0'/p.name).read_bytes(),p
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
subprocess.run(['/usr/bin/python3',str(validator),str(root),str(out),str(refs)],env=env,check=True)
print('PASS exact installed164 NET9 contracts,fresh metadata/NET9 positive/NET8 negative consumer gates')
