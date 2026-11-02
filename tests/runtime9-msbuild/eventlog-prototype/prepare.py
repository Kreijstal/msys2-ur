from pathlib import Path
import shutil,json,subprocess,sys
root=Path(sys.argv[1]).resolve();source=Path('E:/codex-dotnet10/reference9proto1.o2jJA5/r');r=root/'r';r.mkdir()
for n in ['src/libraries/Common','src/libraries/System.Diagnostics.EventLog']:
 shutil.copytree(source/n,r/n,ignore=shutil.ignore_patterns('*.res','*.dll','*.exe','*.pdb'))
for n in ['src/libraries/Directory.Build.targets','src/libraries/Directory.Build.props','src/libraries/NetCoreAppLibrary.props','eng/Versions.props','LICENSE.TXT']:
 p=r/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/n,p)
for n in ['assembly-version-policy.json','file-version.txt']:
 shutil.copyfile(Path('E:/codex-dotnet10/protected9pkg1.EMeOr2/src/prepared')/n,root/n)
subprocess.run([sys.executable,'-X','utf8',str(root/'prepare-library.py'),str(r),str(root/'plan')],check=True)
