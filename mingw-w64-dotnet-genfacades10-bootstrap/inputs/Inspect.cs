using System;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Text.Json;
internal static class Inspect {
 static int Main(string[] args) {
  using var pe=new PEReader(File.OpenRead(args[0]));var md=pe.GetMetadataReader();
  var def=md.GetAssemblyDefinition();
  Console.WriteLine(JsonSerializer.Serialize(new { name=md.GetString(def.Name), references=md.AssemblyReferences.Select(h=>{var r=md.GetAssemblyReference(h);return new {name=md.GetString(r.Name),version=r.Version.ToString()};}), forwards=md.ExportedTypes.Where(h=>md.GetExportedType(h).IsForwarder).Select(h=>{var t=md.GetExportedType(h);return md.GetString(t.Namespace)+"."+md.GetString(t.Name);}).OrderBy(n=>n,StringComparer.Ordinal), publicTypes=md.TypeDefinitions.Where(h=>(md.GetTypeDefinition(h).Attributes&System.Reflection.TypeAttributes.Public)!=0).Select(h=>{var t=md.GetTypeDefinition(h);return md.GetString(t.Namespace)+"."+md.GetString(t.Name);}).OrderBy(n=>n,StringComparer.Ordinal)},new JsonSerializerOptions{WriteIndented=true}));return 0;
 }
}
