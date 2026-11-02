using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;
static class Program
{
    static void Main(string[] args)
    {
        var result=new SortedDictionary<string,object>(StringComparer.Ordinal);
        foreach(string file in args.Skip(1))
        {
            using var assembly=AssemblyDefinition.ReadAssembly(file);
            result[file]=new {identity=assembly.Name.FullName,exported_types=assembly.MainModule.ExportedTypes.Select(t=>new {name=t.FullName,is_forwarder=t.IsForwarder,attributes=t.Attributes.ToString(),scope=t.Scope.ToString()}).OrderBy(t=>t.name,StringComparer.Ordinal).ToArray()};
        }
        File.WriteAllText(args[0],JsonSerializer.Serialize(result,new JsonSerializerOptions{WriteIndented=true})+"\n");
    }
}
