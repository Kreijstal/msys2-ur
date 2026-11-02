using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Mono.Cecil;
using Mono.Cecil.Cil;

sealed class OwnedContext:AssemblyLoadContext
{
    internal static readonly string[] Names={"Microsoft.Build.Tasks.Core","Microsoft.Build.Framework","Microsoft.Build.Utilities.Core","System.Collections.Immutable","System.Reflection.Metadata","System.Threading.Tasks.Dataflow","System.CodeDom","Microsoft.Win32.Registry","System.Text.Encoding.CodePages"};
    readonly string directory;
    public OwnedContext(string directory):base(isCollectible:true){this.directory=directory;}
    protected override Assembly? Load(AssemblyName name)=>Names.Contains(name.Name)?LoadFromAssemblyPath(Path.Combine(directory,name.Name+".dll")):null;
}
static class Program
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static SortedDictionary<string,SortedDictionary<string,string>> Resources(string file)
    {
        using var assembly=AssemblyDefinition.ReadAssembly(file);
        var result=new SortedDictionary<string,SortedDictionary<string,string>>(StringComparer.Ordinal);
        foreach(var embedded in assembly.MainModule.Resources.OfType<EmbeddedResource>())
        {
            var entries=new SortedDictionary<string,string>(StringComparer.Ordinal);
            if(embedded.Name.EndsWith(".resources",StringComparison.Ordinal))
            {
                using var reader=new ResourceReader(embedded.GetResourceStream());var names=reader.GetEnumerator();
                while(names.MoveNext())
                {
                    string name=(string)names.Key;reader.GetResourceData(name,out string type,out byte[] data);
                    Require(type=="ResourceTypeCode.String","Only string resources are decoded: "+name);
                    using var value=new BinaryReader(new MemoryStream(data),Encoding.UTF8);entries[name]=value.ReadString();
                }
            }
            else{using var data=new MemoryStream();embedded.GetResourceStream().CopyTo(data);entries["$sha256"]=Convert.ToHexString(SHA256.HashData(data.ToArray())).ToLowerInvariant();}
            result[embedded.Name]=entries;
        }
        return result;
    }
    static void Main(string[] args)
    {
        if(args[0]=="--dump-resources")
        {
            File.WriteAllText(args[2],JsonSerializer.Serialize(Resources(args[1]),new JsonSerializerOptions{WriteIndented=true})+"\n");return;
        }
        string directory=Path.GetFullPath(args[0]);string file=Path.Combine(directory,"Microsoft.Build.Tasks.Core.dll");
        using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));var expected=baseline.RootElement.GetProperty("Microsoft.Build.Tasks.Core.dll");
        var wanted=expected.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();var actual=Api.Read(file);
        File.WriteAllLines(file+".missing-api.txt",wanted.Except(actual));File.WriteAllLines(file+".extra-api.txt",actual.Except(wanted));Require(wanted.SequenceEqual(actual),"Original Tasks1305 public API inventory");
        using(var assembly=AssemblyDefinition.ReadAssembly(file))
        {
            Require(assembly.Name.FullName==expected.GetProperty("identity").GetString(),"Original Tasks identity");
            Require(assembly.MainModule.AssemblyReferences.Select(x=>x.FullName).OrderBy(x=>x,StringComparer.Ordinal).SequenceEqual(expected.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal)),"Original dependency identity set");
            Require((string)assembly.CustomAttributes.Single(a=>a.AttributeType.FullName=="System.Reflection.AssemblyFileVersionAttribute").ConstructorArguments[0].Value=="16.0.461.62831","Original file version");
            Require((string)assembly.CustomAttributes.Single(a=>a.AttributeType.FullName=="System.Reflection.AssemblyInformationalVersionAttribute").ConstructorArguments[0].Value=="16.0.461+g6ff56ef63c","Original informational version");
            Require((string)assembly.CustomAttributes.Single(a=>a.AttributeType.FullName=="System.Runtime.Versioning.TargetFrameworkAttribute").ConstructorArguments[0].Value==".NETStandard,Version=v2.0","Original NS2 profile");
        }
        var resources=Resources(file);var expectedResources=JsonSerializer.Deserialize<SortedDictionary<string,SortedDictionary<string,string>>>(File.ReadAllText(args[2]))!;
        File.WriteAllText(Path.Combine(directory,"source-resources.json"),JsonSerializer.Serialize(resources,new JsonSerializerOptions{WriteIndented=true})+"\n");
        Require(resources.Count==expectedResources.Count && resources.All(pair=>expectedResources.TryGetValue(pair.Key,out var values) && values.Count==pair.Value.Count && pair.Value.All(value=>values.TryGetValue(value.Key,out var text) && text==value.Value)),"Original published resource strings and embedded file bytes");
        Console.WriteLine($"PASS {resources.Count} original resource sets and {resources.Sum(r=>r.Value.Count)} values/files");
        using(var symbols=ModuleDefinition.ReadModule(file,new ReaderParameters{ReadSymbols=true,SymbolReaderProvider=new PortablePdbReaderProvider()}))
        {
            Require(symbols.SymbolReader!=null && symbols.Types.SelectMany(t=>t.Methods).Count(m=>m.DebugInformation.HasSequencePoints)>100,"Matching source portable PDB and sequence points");
        }
        var context=new OwnedContext(directory);var bridge=context.LoadFromAssemblyPath(Path.Combine(directory,"Bridge.dll"));
        Console.WriteLine(bridge.GetType("TasksBridge")!.GetMethod("Run")!.Invoke(null,new object[]{directory}));
        foreach(var name in OwnedContext.Names)Require(context.Assemblies.Single(a=>a.GetName().Name==name).Location==Path.Combine(directory,name+".dll"),"Exact old runtime dependency: "+name);
        context.Unload();Console.WriteLine("PASS original Tasks1305 API/dependency identities and all nine isolated source implementations");
    }
}
