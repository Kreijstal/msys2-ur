using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text.Json;
using Mono.Cecil;

sealed class OwnedContext:AssemblyLoadContext
{
    readonly string directory;
    public OwnedContext(string directory):base(isCollectible:true){this.directory=directory;}
    protected override Assembly? Load(AssemblyName name)
    {
        if(name.Name=="Microsoft.Win32.Registry" || name.Name=="System.Text.Encoding.CodePages")return LoadFromAssemblyPath(Path.Combine(directory,name.Name+".dll"));return null;
    }
}
static class Program
{
    static void Require(bool value,string name){if(!value)throw new Exception(name);}
    static void Main(string[] args)
    {
        var directory=Path.GetFullPath(args[0]);using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));using var sources=JsonDocument.Parse(File.ReadAllText(args[2]));int total=0,resources=0;
        if(args.Length==5)
        {
            using var referenceBaseline=JsonDocument.Parse(File.ReadAllText(args[4]));int count=0;
            foreach(var name in new[]{"Microsoft.Win32.Registry","System.Text.Encoding.CodePages"})
            {
                string path=Path.Combine(args[3],name+".dll");var expected=referenceBaseline.RootElement.GetProperty(name+".dll");var api=expected.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();Require(api.SequenceEqual(Api.Read(path)),name+" original compile-time API");
                using var reference=AssemblyDefinition.ReadAssembly(path);Require(reference.Name.FullName==expected.GetProperty("identity").GetString(),name+" original reference identity");
                Require(reference.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"),name+" reference-only marker");
                Require(reference.MainModule.AssemblyReferences.Select(x=>x.FullName).OrderBy(x=>x,StringComparer.Ordinal).SequenceEqual(expected.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal)),name+" original reference dependency identities");count+=api.Length;
            }
            Console.WriteLine($"PASS {count} original compile-time reference entries and exact reference identities");
        }
        foreach(var name in new[]{"Microsoft.Win32.Registry","System.Text.Encoding.CodePages"})
        {
            string path=Path.Combine(directory,name+".dll");var expected=baseline.RootElement.GetProperty(name+".dll");var wanted=expected.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();var actual=Api.Read(path);
            if(!wanted.SequenceEqual(actual))
            {
                File.WriteAllLines(path+".missing-api.txt",wanted.Except(actual));File.WriteAllLines(path+".extra-api.txt",actual.Except(wanted));throw new Exception(name+" original public API mismatch");
            }
            total+=wanted.Length;using var assembly=AssemblyDefinition.ReadAssembly(path);
            Require(assembly.Name.FullName==expected.GetProperty("identity").GetString(),name+" original identity");
            var references=assembly.MainModule.AssemblyReferences.Select(x=>x.FullName).OrderBy(x=>x,StringComparer.Ordinal).ToArray();var expectedRefs=expected.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
            if(!references.SequenceEqual(expectedRefs)){File.WriteAllLines(path+".actual-references.txt",references);File.WriteAllLines(path+".expected-references.txt",expectedRefs);throw new Exception(name+" original runtime reference identity mismatch");}
            Require(!assembly.CustomAttributes.Any(x=>x.AttributeType.FullName=="System.Runtime.Versioning.TargetFrameworkAttribute"),name+" original no TFM attribute policy");
            var input=sources.RootElement.GetProperty("libraries").GetProperty(name);var strings=input.GetProperty("resources");
            var res=assembly.MainModule.Resources.OfType<EmbeddedResource>().Single(x=>x.Name=="FxResources."+name+".SR.resources");using var reader=new ResourceReader(res.GetResourceStream());var values=reader.Cast<DictionaryEntry>().ToDictionary(x=>(string)x.Key,x=>(string)x.Value!);
            Require(values.Count==strings.EnumerateObject().Count(),name+" resource count");foreach(var pair in strings.EnumerateObject()){Require(values[pair.Name]==pair.Value.GetString(),name+" resource "+pair.Name);resources++;}
            if(name=="System.Text.Encoding.CodePages")
            {
                var data=assembly.MainModule.Resources.OfType<EmbeddedResource>().Single(x=>x.Name=="codepages.nlp").GetResourceData();string hash=Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
                Require(hash==input.GetProperty("original_file_sha256").GetProperty("src/System.Text.Encoding.CodePages/src/Data/codepages.nlp").GetString(),"Exact original codepages.nlp bytes");
            }
        }
        var context=new OwnedContext(directory);var bridge=context.LoadFromAssemblyPath(Path.Combine(directory,"Bridge.dll"));Console.WriteLine(bridge.GetType("Bridge")!.GetMethod("Run")!.Invoke(null,null));
        foreach(var name in new[]{"Microsoft.Win32.Registry","System.Text.Encoding.CodePages"})Require(context.Assemblies.Single(a=>a.GetName().Name==name).Location==Path.Combine(directory,name+".dll"),"Must execute candidate bytes: "+name);
        context.Unload();Console.WriteLine($"PASS {total} original public API entries, exact dependency identities, {resources} source strings and original encoding data; isolated original libraries executed");
    }
}
