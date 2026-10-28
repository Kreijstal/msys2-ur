using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;

internal static class GenerateFacades
{
    private sealed class Context(string directory) : AssemblyLoadContext(true)
    {
        protected override Assembly? Load(AssemblyName name)
        {
            string path=Path.Combine(directory,name.Name+".dll");
            return File.Exists(path)?LoadFromAssemblyPath(path):null;
        }
    }
    private static string CSharpName(Type type)
    {
        string name="global::"+type.FullName!;
        if(!type.IsGenericTypeDefinition) return name;
        int tick=name.IndexOf('`');
        return name[..tick]+"<"+new string(',',type.GetGenericArguments().Length-1)+">";
    }
    private static int Main(string[] args)
    {
        if(args.Length!=3) throw new ArgumentException("usage: generate-facades CONTRACT_ASSETS IMPLEMENTATION_ASSETS OUTPUT");
        var contracts=new Context(Path.GetFullPath(args[0]));
        var implementation=new Context(Path.GetFullPath(args[1]));
        var actual=implementation.LoadFromAssemblyPath(Path.Combine(Path.GetFullPath(args[1]),"System.Private.ServiceModel.dll"));
        Directory.CreateDirectory(args[2]);
        var records=new List<object>();
        foreach(var path in Directory.GetFiles(args[0],"*.dll").Order()) {
            var contract=contracts.LoadFromAssemblyPath(Path.GetFullPath(path));
            var lines=new List<string>();
            var types=contract.GetExportedTypes().Concat(contract.GetForwardedTypes()).Distinct()
                .Where(t=>!t.IsNested).OrderBy(t=>t.FullName).ToArray();
            foreach(var type in types) {
                var target=actual.GetType(type.FullName!,throwOnError:true)!;
                if(!target.IsPublic) throw new Exception("Forward target is not public: "+type.FullName);
                lines.Add("[assembly: System.Runtime.CompilerServices.TypeForwardedTo(typeof("+CSharpName(type)+"))]");
            }
            string output=Path.Combine(args[2],contract.GetName().Name!+".cs");
            File.WriteAllLines(output,lines);
            records.Add(new { assembly=contract.GetName().Name, types=types.Select(t=>t.FullName).ToArray() });
            Console.WriteLine("Generated "+types.Length+" root type forwards for "+contract.GetName().Name);
        }
        File.WriteAllText(Path.Combine(args[2],"type-forwards.json"),JsonSerializer.Serialize(records,new JsonSerializerOptions { WriteIndented=true }));
        return 0;
    }
}
