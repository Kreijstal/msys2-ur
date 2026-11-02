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
        foreach(var name in new[]{"mscorlib.dll","System.Numerics.dll"})
        {
            string file=Path.Combine(args[0],name);var expected=baseline.RootElement.GetProperty(name);var actual=Api.Read(file);var wanted=expected.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();
            File.WriteAllLines(file+".missing-api.txt",wanted.Except(actual));File.WriteAllLines(file+".extra-api.txt",actual.Except(wanted));if(!wanted.SequenceEqual(actual))throw new Exception("Full original API "+name);
            using var assembly=AssemblyDefinition.ReadAssembly(file);if(assembly.Name.FullName!=expected.GetProperty("identity").GetString())throw new Exception("Identity "+name);
            if(!assembly.MainModule.AssemblyReferences.Select(a=>a.FullName).OrderBy(x=>x,StringComparer.Ordinal).SequenceEqual(expected.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal)))throw new Exception("References "+name);
            if(!assembly.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"))throw new Exception("Must remain reference-only "+name);
            if(assembly.MainModule.RuntimeVersion!="v4.0.30319")throw new Exception("Original metadata runtime version");
            count+=wanted.Length;Console.WriteLine("PASS "+name+" "+wanted.Length+" original API entries, exact identity/dependencies and reference-only marker");
        }
        Console.WriteLine("PASS all "+count+" original Framework4.6.2 public API entries");
    }
}
