using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using System.Text.Json;
using Mono.Cecil;
sealed class OwnedContext : AssemblyLoadContext
{
    readonly string directory;
    public OwnedContext(string directory):base(isCollectible:true){this.directory=directory;}
    protected override Assembly? Load(AssemblyName name)=>name.Name=="System.Threading.Tasks.Dataflow" ? LoadFromAssemblyPath(Path.Combine(directory,name.Name+".dll")) : null;
}
static class Program
{
    static void Require(bool condition,string message){if(!condition)throw new Exception(message);}
    static void Main(string[] args)
    {
        string directory=Path.GetFullPath(args[0]);
        using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));
        using var source=JsonDocument.Parse(File.ReadAllText(args[2]));
        var expected=baseline.RootElement.GetProperty("System.Threading.Tasks.Dataflow.dll");
        string file=Path.Combine(directory,"System.Threading.Tasks.Dataflow.dll");
        Require(Api.Read(file).SequenceEqual(expected.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!)),"original API inventory");
        using var assembly=AssemblyDefinition.ReadAssembly(file);
        Require(assembly.Name.FullName==expected.GetProperty("identity").GetString(),"original assembly identity");
        Require(assembly.MainModule.AssemblyReferences.Select(x=>x.FullName).OrderBy(x=>x,StringComparer.Ordinal).SequenceEqual(expected.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal)),"original dependency identities");
        var expectedResources=source.RootElement.GetProperty("profiles").GetProperty(args[3]).GetProperty("resources");
        var embedded=assembly.MainModule.Resources.OfType<EmbeddedResource>().ToArray();
        Require(embedded.Length==1,"source resource count");
        using var reader=new ResourceReader(embedded[0].GetResourceStream());
        var values=reader.Cast<DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value!);
        Require(values.Count==expectedResources.EnumerateObject().Count(),"resource keys");
        foreach(var item in expectedResources.EnumerateObject())Require(values[item.Name]==item.Value.GetString(),"source resource "+item.Name);
        var context=new OwnedContext(directory);
        var bridge=context.LoadFromAssemblyPath(Path.Combine(directory,"Bridge.dll"));
        Console.WriteLine(bridge.GetType("Bridge")!.GetMethod("Run")!.Invoke(null,null));
        Require(context.Assemblies.Single(a=>a.GetName().Name=="System.Threading.Tasks.Dataflow").Location==file,"must execute exact old implementation");
        context.Unload();
        Console.WriteLine($"PASS {args[3]}: 269 original API entries, exact dependency identities and {values.Count} source resource values");
    }
}
