using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using System.Text.Json;
using Mono.Cecil;
sealed class OwnedContext:AssemblyLoadContext
{
    readonly string folder;
    public OwnedContext(string folder):base(isCollectible:true){this.folder=folder;}
    protected override Assembly? Load(AssemblyName name)
    {
        bool own=(name.Name=="System.Memory" && name.Version==new Version(4,0,1,1)) || (name.Name=="System.Buffers" && name.Version==new Version(4,0,2,0)) || (name.Name=="System.Runtime.CompilerServices.Unsafe" && name.Version==new Version(4,0,4,1)) || (name.Name=="System.Numerics.Vectors" && name.Version==new Version(4,1,3,0));
        return own?LoadFromAssemblyPath(Path.Combine(folder,name.Name+".dll")):null;
    }
}
static class Program
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static Dictionary<string,Dictionary<string,string>> Resources(string path)
    {
        using var assembly=AssemblyDefinition.ReadAssembly(path);var result=new Dictionary<string,Dictionary<string,string>>();
        foreach(var resource in assembly.MainModule.Resources.OfType<EmbeddedResource>())
        {
            using var reader=new ResourceReader(resource.GetResourceStream());var data=new Dictionary<string,string>();
            foreach(DictionaryEntry item in reader){Require(item.Value is string,"String resource only");data[(string)item.Key]=(string)item.Value!;}
            result[resource.Name]=data;
        }
        return result;
    }
    static void Execute(string file,string method)
    {
        var context=new OwnedContext(Path.GetDirectoryName(file)!);var bridge=context.LoadFromAssemblyPath(Path.Combine(Path.GetDirectoryName(file)!,"Bridge.dll"));
        Console.WriteLine(bridge.GetType("Bridge")!.GetMethod(method)!.Invoke(null,null));
        Require(context.Assemblies.Single(a=>a.GetName().Name=="System.Memory").Location==file,"Must execute exact candidate Memory4.5.3 DLL");foreach(var name in new[]{"System.Buffers","System.Runtime.CompilerServices.Unsafe"})Require(context.Assemblies.Single(a=>a.GetName().Name==name).Location==Path.Combine(Path.GetDirectoryName(file)!,name+".dll"),"Exact old dependency "+name);if(File.Exists(Path.Combine(Path.GetDirectoryName(file)!,"System.Numerics.Vectors.dll")))Require(context.Assemblies.Single(a=>a.GetName().Name=="System.Numerics.Vectors").Location==Path.Combine(Path.GetDirectoryName(file)!,"System.Numerics.Vectors.dll"),"Exact old Vectors dependency");context.Unload();
    }
    static void Main(string[] args)
    {
        if(args[0]=="--resources"){File.WriteAllText(args[2],JsonSerializer.Serialize(Resources(args[1]),new JsonSerializerOptions{WriteIndented=true})+"\n");return;}
        string file=Path.GetFullPath(args[0]);if(args[1]=="--events"){Execute(file,"Events");return;}
        using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));var expected=baseline.RootElement.GetProperty("System.Memory.dll");
        var wanted=expected.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();var actual=Api.Read(file);
        File.WriteAllLines(file+".missing-api.txt",wanted.Except(actual));File.WriteAllLines(file+".extra-api.txt",actual.Except(wanted));Require(wanted.SequenceEqual(actual),"Original Memory public API");
        bool reference=args[2]=="--reference";
        using(var assembly=AssemblyDefinition.ReadAssembly(file))
        {
            Require(assembly.Name.FullName==expected.GetProperty("identity").GetString(),"Original assembly identity");
            Require(assembly.MainModule.AssemblyReferences.Select(x=>x.FullName).OrderBy(x=>x,StringComparer.Ordinal).SequenceEqual(expected.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal)),"Original dependency identities");
            Require(assembly.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute")==reference,"Original reference/runtime distinction");
            foreach(var attribute in expected.GetProperty("attributes").EnumerateArray())
            {
                string type=attribute.GetProperty("type").GetString()!;
                if(!type.StartsWith("System.Reflection.",StringComparison.Ordinal) && type!="System.CLSCompliantAttribute" && type!="System.Resources.NeutralResourcesLanguageAttribute" && type!="System.Security.AllowPartiallyTrustedCallersAttribute" && type!="System.Runtime.InteropServices.DefaultDllImportSearchPathsAttribute")continue;
                var values=attribute.GetProperty("arguments").EnumerateArray().Select(x=>x.GetString()).ToArray();
                Require(assembly.CustomAttributes.Any(a=>a.AttributeType.FullName==type && a.ConstructorArguments.Select(x=>Convert.ToString(x.Value,CultureInfo.InvariantCulture)).SequenceEqual(values)),"Original managed attribute "+type);
            }
        }
        using var policy=JsonDocument.Parse(File.ReadAllText(args[3]));var native=FileVersionInfo.GetVersionInfo(file);
        foreach(var property in policy.RootElement.GetProperty(args[4]).EnumerateObject())
        {
            var value=typeof(FileVersionInfo).GetProperty(property.Name)!.GetValue(native);
            Require(value is bool boolean ? boolean==property.Value.GetBoolean() : value is int number ? number==property.Value.GetInt32() : (string?)value==property.Value.GetString(),"Original native VERSIONINFO "+property.Name);
        }
        if(reference){Require(Resources(file).Count==0,"Reference has no runtime resources");Console.WriteLine("PASS original reference API/identity/dependencies/marker and managed/native version metadata");return;}
        var expectedResources=JsonSerializer.Deserialize<Dictionary<string,Dictionary<string,string>>>(File.ReadAllText(args[2]))!;var actualResources=Resources(file);
        Require(expectedResources.Count==actualResources.Count && expectedResources.All(p=>actualResources.TryGetValue(p.Key,out var values) && values.Count==p.Value.Count && p.Value.All(v=>values.TryGetValue(v.Key,out var text) && text==v.Value)),"All original resource names and string values");
        Execute(file,"Run");Console.WriteLine("PASS 432 original API entries, exact identity/dependencies/resources and managed/native version metadata");
    }
}
