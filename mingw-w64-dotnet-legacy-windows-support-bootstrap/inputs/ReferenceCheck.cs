using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;
static class Program
{
    static void Main(string[] args)
    {
        using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));int count=0;
        foreach(var name in new[]{"Microsoft.Win32.Registry","System.Text.Encoding.CodePages"})
        {
            string path=Path.Combine(args[0],name,"contract",name+".dll");var expected=baseline.RootElement.GetProperty(name+".dll");var wanted=expected.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();var actual=Api.Read(path);
            if(!wanted.SequenceEqual(actual)){File.WriteAllLines(path+".missing-api.txt",wanted.Except(actual));File.WriteAllLines(path+".extra-api.txt",actual.Except(wanted));throw new Exception(name+" original reference API mismatch");}
            using var assembly=AssemblyDefinition.ReadAssembly(path);
            if(assembly.Name.FullName!=expected.GetProperty("identity").GetString())throw new Exception(name+" original reference identity");
            if(!assembly.MainModule.AssemblyReferences.Select(x=>x.FullName).OrderBy(x=>x,StringComparer.Ordinal).SequenceEqual(expected.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal)))throw new Exception(name+" original reference dependencies");
            if(!assembly.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"))throw new Exception(name+" reference-only marker");
            count+=wanted.Length;
        }
        Console.WriteLine($"PASS {count} original reference API entries, identities, dependency identities and reference-only markers");
    }
}
