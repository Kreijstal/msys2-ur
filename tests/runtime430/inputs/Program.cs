using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;
static class Program {
 static void Main(string[] args) {
  var records=new Dictionary<string,object>();
  foreach(var path in args.Skip(1)) {
   using var asm=AssemblyDefinition.ReadAssembly(path);
   records[Path.GetFileName(path)]=new { identity=asm.Name.FullName,
    attributes=asm.CustomAttributes.Select(a=>new {type=a.AttributeType.FullName,arguments=a.ConstructorArguments.Select(v=>v.Value?.ToString()).ToArray()}).ToArray(),
    references=asm.MainModule.AssemblyReferences.Select(a=>a.FullName).ToArray(),api=Api.Read(path)};
  }
  File.WriteAllText(args[0],JsonSerializer.Serialize(records,new JsonSerializerOptions {WriteIndented=true})+"\n");
 }
}
