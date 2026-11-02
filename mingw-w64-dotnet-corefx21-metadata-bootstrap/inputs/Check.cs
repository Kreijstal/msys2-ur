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
    protected override Assembly? Load(AssemblyName name)
    {
        if(name.Name=="System.Collections.Immutable" || name.Name=="System.Reflection.Metadata")return LoadFromAssemblyPath(Path.Combine(directory,name.Name+".dll"));
        return null;
    }
}
static class Program
{
    static void Require(bool value,string name){if(!value)throw new Exception(name);}
    static void Main(string[] args)
    {
        var directory=Path.GetFullPath(args[0]);using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));using var sources=JsonDocument.Parse(File.ReadAllText(args[2]));
        int entries=0,resources=0;
        foreach(var name in new[]{"System.Collections.Immutable","System.Reflection.Metadata"})
        {
            var path=Path.Combine(directory,name+".dll");var expected=baseline.RootElement.GetProperty(name+".dll");
            var api=expected.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();var actual=Api.Read(path);
            if(!api.SequenceEqual(actual))
            {
                File.WriteAllLines(Path.Combine(directory,name+".missing-api.txt"),api.Except(actual));File.WriteAllLines(Path.Combine(directory,name+".extra-api.txt"),actual.Except(api));
                throw new Exception(name+" original API mismatch");
            }
            entries+=api.Length;
            using var assembly=AssemblyDefinition.ReadAssembly(path);
            Require(assembly.Name.FullName==expected.GetProperty("identity").GetString(),name+" assembly identity");
            Require(assembly.MainModule.AssemblyReferences.Select(x=>x.FullName).SequenceEqual(expected.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!)),name+" original assembly references");
            Require(!assembly.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.Versioning.TargetFrameworkAttribute"),name+" original no TFM attribute policy");
            var expectedResources=sources.RootElement.GetProperty("libraries").GetProperty(name).GetProperty("resources");
            var embedded=assembly.MainModule.Resources.OfType<EmbeddedResource>().ToArray();Require(embedded.Length==1,name+" resource count");
            using var reader=new ResourceReader(embedded[0].GetResourceStream());var values=reader.Cast<DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value!);
            Require(values.Count==expectedResources.EnumerateObject().Count(),name+" resource keys");
            foreach(var item in expectedResources.EnumerateObject()){Require(values[item.Name]==item.Value.GetString(),name+" resource "+item.Name);resources++;}
        }
        var context=new OwnedContext(directory);var bridge=context.LoadFromAssemblyPath(Path.Combine(directory,"Bridge.dll"));
        Console.WriteLine(bridge.GetType("Bridge")!.GetMethod("Run")!.Invoke(null,null));
        foreach(var name in new[]{"System.Collections.Immutable","System.Reflection.Metadata"})Require(context.Assemblies.Single(a=>a.GetName().Name==name).Location==Path.Combine(directory,name+".dll"),"Must run exact candidate bytes for "+name);
        context.Unload();
        Console.WriteLine($"PASS {entries} original API entries, exact runtime dependency tables and {resources} source resource values; isolated original versions executed");
    }
}
