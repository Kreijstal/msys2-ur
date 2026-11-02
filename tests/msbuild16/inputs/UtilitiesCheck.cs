using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
using System.Collections;
using System.Resources;
using Mono.Cecil;

sealed class OwnedContext:AssemblyLoadContext
{
    readonly string directory;
    public OwnedContext(string directory):base(isCollectible:true){this.directory=directory;}
    protected override Assembly? Load(AssemblyName name)
    {
        if(new[]{"Microsoft.Build.Utilities.Core","Microsoft.Build.Framework","System.Collections.Immutable","Microsoft.Win32.Registry","System.Text.Encoding.CodePages"}.Contains(name.Name))return LoadFromAssemblyPath(Path.Combine(directory,name.Name+".dll"));return null;
    }
}
static class Program
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static void Main(string[] args)
    {
        string path=Path.Combine(args[0],"Microsoft.Build.Utilities.Core.dll");using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));
        var wanted=baseline.RootElement.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();var actual=Api.Read(path);
        if(!wanted.SequenceEqual(actual)){File.WriteAllLines(path+".missing-api.txt",wanted.Except(actual));File.WriteAllLines(path+".extra-api.txt",actual.Except(wanted));throw new Exception("Original 487-entry Utilities metadata mismatch");}
        using(var assembly=AssemblyDefinition.ReadAssembly(path))
        {
            Require(assembly.Name.FullName==baseline.RootElement.GetProperty("identity").GetString(),"Original assembly identity");
            Require(assembly.MainModule.AssemblyReferences.Select(x=>x.FullName).OrderBy(x=>x,StringComparer.Ordinal).SequenceEqual(baseline.RootElement.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal)),"Original dependency identity set");
            Require(assembly.CustomAttributes.Single(a=>a.AttributeType.FullName=="System.Runtime.Versioning.TargetFrameworkAttribute").ConstructorArguments[0].Value.ToString()==".NETStandard,Version=v2.0","Original NS2 profile");
            Require(assembly.CustomAttributes.Single(a=>a.AttributeType.FullName=="System.Reflection.AssemblyFileVersionAttribute").ConstructorArguments[0].Value.ToString()=="16.0.461.62831","Original file version");
            Require(assembly.CustomAttributes.Single(a=>a.AttributeType.FullName=="System.Reflection.AssemblyInformationalVersionAttribute").ConstructorArguments[0].Value.ToString()=="16.0.461+g6ff56ef63c","Original informational version");
            using var audit=JsonDocument.Parse(File.ReadAllText(args[2]));int resourceCount=0;
            foreach(var resource in audit.RootElement.GetProperty("source_resources").EnumerateObject())
            {
                string logical="Microsoft.Build.Utilities.Core."+(resource.Name=="Strings.resx"?"Strings":"Strings.shared")+".resources";
                var embedded=assembly.MainModule.Resources.OfType<EmbeddedResource>().Single(r=>r.Name==logical);using var reader=new ResourceReader(embedded.GetResourceStream());var values=reader.Cast<DictionaryEntry>().ToDictionary(p=>(string)p.Key,p=>(string)p.Value!);
                Require(values.Count==resource.Value.EnumerateObject().Count(),"Original resource count "+logical);
                foreach(var item in resource.Value.EnumerateObject()){Require(values[item.Name]==item.Value.GetString(),"Original resource "+item.Name);resourceCount++;}
            }
            Console.WriteLine($"PASS {resourceCount} original Utilities/shared resource strings");
        }
        var context=new OwnedContext(Path.GetFullPath(args[0]));var bridge=context.LoadFromAssemblyPath(Path.Combine(Path.GetFullPath(args[0]),"Bridge.dll"));Console.WriteLine(bridge.GetType("UtilitiesBridge")!.GetMethod("Run")!.Invoke(null,null));
        foreach(var name in new[]{"Microsoft.Build.Utilities.Core","Microsoft.Build.Framework"})Require(context.Assemblies.Single(a=>a.GetName().Name==name).Location==Path.Combine(Path.GetFullPath(args[0]),name+".dll"),"Exact candidate runtime assembly: "+name);
        context.Unload();Console.WriteLine("PASS 487 original Utilities API entries, original dependency identities and isolated source implementations");
    }
}
