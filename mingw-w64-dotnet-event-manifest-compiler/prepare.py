#!/usr/bin/env python3
"""Build EventTraceKit's manifest/resource compiler with the installed .NET SDK."""
from pathlib import Path
import shutil
import sys

source, output = map(Path, sys.argv[1:])
output.mkdir(parents=True)
library = output / "EventTracing"
shutil.copytree(source / "src/EventTraceKit.EventTracing", library)

# The standalone driver creates its compiler directly; MEF discovery belongs
# to upstream's Visual Studio extension and is not needed by this driver.
for name in ("ICodeGenerator", "CxxCodeGenerator", "McCodeGenerator"):
    path = library / f"Compilation/CodeGen/{name}.cs"
    text = path.read_text().replace("    using System.ComponentModel.Composition;\n", "")
    text = text.replace("CodeGeneratorAttribute : ExportAttribute", "CodeGeneratorAttribute : Attribute")
    text = text.replace("\n            : base(typeof(ICodeGeneratorProvider))", "")
    text = text.replace("        [ImportingConstructor]\n", "")
    path.write_text(text)

# .NET 8 removed the Framework-only MemoryMappedFileSecurity argument. Null
# meant default OS security, which is also the six-argument overload's default.
path = library / "Compilation/Support/MemoryMappedViewWriter.cs"
text = path.read_text()
old = "MemoryMappedFileAccess.ReadWrite,\n                null,\n                HandleInheritability.None,"
assert text.count(old) == 1
path.write_text(text.replace(old, "MemoryMappedFileAccess.ReadWrite,\n                HandleInheritability.None,"))

(output / "Compiler.csproj").write_text('''<Project Sdk="Microsoft.NET.Sdk">
 <PropertyGroup>
  <TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType>
  <AssemblyName>event-manifest-compiler</AssemblyName>
  <UseAppHost>false</UseAppHost><AllowUnsafeBlocks>true</AllowUnsafeBlocks>
  <EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers>
  <GenerateAssemblyInfo>false</GenerateAssemblyInfo><NuGetAudit>false</NuGetAudit>
 </PropertyGroup>
 <ItemGroup>
  <Compile Include="EventTracing/**/*.cs" Exclude="EventTracing/Compilation/ResGen/EventTemplateDumperFast.cs;EventTracing/Properties/AssemblyInfo.cs" />
  <Compile Include="Program.cs" />
  <EmbeddedResource Include="EventTracing/Schema/Extensions.xsd" LogicalName="EventTraceKit.EventTracing.Schema.Extensions.xsd" />
 </ItemGroup>
</Project>
''')
(output / "NuGet.config").write_text('<configuration><packageSources><clear /></packageSources></configuration>\n')
shutil.copyfile(Path(__file__).with_name("Program.cs"), output / "Program.cs")
