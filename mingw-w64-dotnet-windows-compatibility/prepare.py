"""Preserve the complete original Windows compatibility metapackage graph."""
from pathlib import Path
import argparse,copy,hashlib,json,tarfile,xml.etree.ElementTree as E

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('windowsdesktop',type=Path);parser.add_argument('arcade',type=Path);parser.add_argument('destination',type=Path)
args=parser.parse_args();out=args.destination.resolve();assert not out.exists(),out
sha=lambda data:hashlib.sha256(data).hexdigest()
commit='337963009d48a3016b50172b451b4e80f78791a7';arcade='444c2ef3c414558e2e409ee346f1faebb19687eb'
assert sha(args.windowsdesktop.read_bytes())=='e5f9b43643a3dfdf1afae7e2f3f54d5e140513191c82dadcc56301b9cb494b94'
assert sha(args.arcade.read_bytes())=='a4e0e24eb4238b692e4407c4fb0e5fa4db2ee79c8033bb7d2a40e3fb7164604f'
paths=['eng/Versions.props','eng/Version.Details.xml','Directory.Build.props','LICENSE','src/Microsoft.Windows.Compatibility/src/Microsoft.Windows.Compatibility.csproj','src/Microsoft.Windows.Compatibility/src/PACKAGE.md']
records={};out.mkdir();source=out/'source';source.mkdir()
with tarfile.open(args.windowsdesktop) as tar:
 assert tar.pax_headers['comment']==commit
 for relative in paths:
  data=tar.extractfile('windowsdesktop-'+commit+'/'+relative).read();p=source/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);records[relative]=sha(data)
assert E.parse(source/'eng/Version.Details.xml').find(".//Dependency[@Name='Microsoft.DotNet.Arcade.Sdk']/Sha").text==arcade
asset='src/Microsoft.DotNet.Arcade.Sdk/tools/Assets/DotNetPackageIcon.png'
with tarfile.open(args.arcade) as tar:
 data=tar.extractfile('arcade-'+arcade+'/'+asset).read();(out/'Icon.png').write_bytes(data);icon_sha=sha(data)
 (out/'Arcade-LICENSE.TXT').write_bytes(tar.extractfile('arcade-'+arcade+'/LICENSE.TXT').read())
project=E.parse(source/paths[-2]);assert project.getroot().get('Sdk')=='Microsoft.Build.NoTargets'
project.getroot().attrib.pop('Sdk');E.ElementTree(project.getroot()).write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
# This view evaluates only package metadata. The original five target framework
# groups and every PackageReference/condition remain unchanged. Packing is done
# by the installed source-built NuGet library; no compile outputs exist upstream.
wrapper=E.Element('Project');props=E.SubElement(wrapper,'PropertyGroup')
for name,value in dict(NetCurrent='net8.0',NetPrevious='net7.0',NetMinimum='net6.0').items():E.SubElement(props,name).text=value
E.SubElement(wrapper,'Import',Project='source/eng/Versions.props');E.SubElement(wrapper,'Import',Project='upstream.proj')
E.ElementTree(wrapper).write(out/'Evaluate.proj',encoding='utf-8',xml_declaration=True)
report=dict(source_commit=commit,source_archive_sha256=sha(args.windowsdesktop.read_bytes()),original_file_sha256=records,original_project_sdk='Microsoft.Build.NoTargets',metadata_only_adapter='Remove SDK import for metadata evaluation only; source NuGet.Packaging creates the codeless package',production_csharp_changes=[],arcade_source_commit=arcade,original_icon_path=asset,icon_sha256=icon_sha,full_dependency_goal_complete=False)
(out/'source-inputs.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS pinned complete metapackage project/version/readme/license inputs and source Arcade icon; no implementation binaries extracted')
