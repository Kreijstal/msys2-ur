"""Replace bootstrap-only analyzer import stubs with optional package forwarding imports."""
from pathlib import Path
import sys
sdk=Path(sys.argv[1]);root=sdk/'Sdks/Microsoft.NET.Sdk/analyzers/build'
marker='m612 bootstrap: placeholder, dotnet/roslyn-analyzers not built'
for extension in ['props','targets']:
 path=root/('Microsoft.CodeAnalysis.NetAnalyzers.'+extension)
 text=path.read_text(encoding='utf-8-sig')
 if marker not in text:
  print('Retain non-placeholder SDK analyzer import:',path.name);continue
 target='SourceBuild.NetAnalyzers.'+extension
 path.write_text('<Project>\n  <!-- Source analyzer implementation is supplied by dotnet-sdk-netanalyzers. -->\n  <Import Project="$(MSBuildThisFileDirectory)'+target+'" Condition="Exists(\'$(MSBuildThisFileDirectory)'+target+'\')" />\n</Project>\n')
 print('Forward bootstrap analyzer import:',path.name,'->',target)
