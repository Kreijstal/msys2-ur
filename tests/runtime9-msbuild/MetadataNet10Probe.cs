using System;
using System.IO;
using System.Linq;
using System.Reflection;
internal static class MetadataNet10Probe
{
    static void Require(bool condition,string message) { if(!condition)throw new Exception(message); }
    static int Main(string[] args)
    {
        string runtime=Path.GetDirectoryName(typeof(object).Assembly.Location)!;
        string compiler=args[0];
        var paths=Directory.GetFiles(runtime,"*.dll").Concat(Directory.GetFiles(compiler,"*.dll"));
        using(var context=new MetadataLoadContext(new PathAssemblyResolver(paths),"System.Private.CoreLib"))
        {
            Require(context.CoreAssembly!.GetName().Version==new Version(10,0,0,0),"Original NET10 core metadata");
            var assembly=context.LoadFromAssemblyPath(Path.Combine(compiler,"Microsoft.CodeAnalysis.CSharp.dll"));
            var type=assembly.GetType("Microsoft.CodeAnalysis.CSharp.CSharpCompilation",true)!;
            Require(type.GetMethods(BindingFlags.Public|BindingFlags.Static|BindingFlags.DeclaredOnly).Any(m=>m.Name=="Create"&&m.ReturnType.FullName==type.FullName),"Original NET10 source Roslyn compilation factory metadata");
            var host=context.LoadFromAssemblyPath(Path.Combine(compiler,"csc.dll"));
            Require(host.EntryPoint!=null,"Original NET10 csc entry-point metadata");
            Require(!AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetName().Name is "Microsoft.CodeAnalysis" or "Microsoft.CodeAnalysis.CSharp" or "csc"),"Inspected compiler assemblies never loaded for execution");
        }
        Console.WriteLine("PASS MetadataLoadContext9.0.11 inspects real source NET10 CoreLib,Roslyn factory and csc entry point without runtime loading");
        return 0;
    }
}
