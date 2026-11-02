using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;
static class Program
{
 static void Need(bool value,string label){if(!value)throw new Exception(label);}
 static void Main(string[] args)
 {
  using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));int count=0;
  foreach(var item in baseline.RootElement.EnumerateObject())
  {
   var file=Path.Combine(args[0],item.Name);var expected=item.Value.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();var actual=Api.Read(file);
   File.WriteAllLines(file+".missing-api.txt",expected.Except(actual));File.WriteAllLines(file+".extra-api.txt",actual.Except(expected));Need(expected.SequenceEqual(actual),item.Name+" original public API");
   using var a=AssemblyDefinition.ReadAssembly(file);Need(a.Name.FullName==item.Value.GetProperty("identity").GetString(),item.Name+" identity");
   Need(a.CustomAttributes.Any(x=>x.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"),item.Name+" reference-only marker");
   Need(a.MainModule.AssemblyReferences.Select(x=>x.FullName).OrderBy(x=>x,StringComparer.Ordinal).SequenceEqual(item.Value.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal)),item.Name+" dependency identities");
   count+=expected.Length;Console.WriteLine("PASS "+item.Name+" "+expected.Length+" original API entries, identity, reference marker and dependency identities");
  }
  Console.WriteLine("PASS "+count+" original reference API entries");
 }
}
