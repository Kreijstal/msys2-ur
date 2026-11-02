using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Loader;
using System.Text.Json;

internal static class Program
{
    static void Require(bool ok,string message){if(!ok)throw new Exception(message);}
    sealed class Isolated : AssemblyLoadContext
    {
        readonly string build,consumer;
        public Isolated(string folder,string library):base("source-humanizer-netstandard",true){build=folder;consumer=library;}
        protected override Assembly? Load(AssemblyName name)
        {
            if(name.Name=="Humanizer")return LoadFromAssemblyPath(Path.Combine(build,"Humanizer.dll"));
            if(name.Name=="StandardHumanizerConsumer")return LoadFromAssemblyPath(Path.Combine(consumer,"StandardHumanizerConsumer.dll"));
            return null;
        }
    }
    static int Main(string[] args)
    {
        using var config=JsonDocument.Parse(File.ReadAllText(args[0]));var settings=config.RootElement;
        string build=settings.GetProperty("build_output").GetString()!,consumer=settings.GetProperty("consumer_output").GetString()!;
        var context=new Isolated(build,consumer);
        var assembly=context.LoadFromAssemblyPath(Path.Combine(build,"Humanizer.dll"));var identity=assembly.GetName();
        Require(identity.Version==new Version(2,14,0,0),"Assembly version");
        Require(identity.GetPublicKeyToken()!.SequenceEqual(Convert.FromHexString(settings.GetProperty("expected_public_key_token").GetString()!)),"Original signing identity");
        Require(identity.GetPublicKey()!.SequenceEqual(Convert.FromHexString(settings.GetProperty("expected_public_key_hex").GetString()!)),"Original complete public signing key");
        Require(assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName==".NETStandard,Version=v2.0","Original target framework");
        Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version=="2.14.1.0","File version");
        Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion=="2.14.1+3ebc38de585fc641a04b0e78ed69468453b0f8a1","Source revision");
        var manager=new ResourceManager("Humanizer.Properties.Resources",assembly);int sets=0,values=0;
        foreach(var expected in settings.GetProperty("resources").EnumerateArray())
        {
            string culture=expected.GetProperty("culture").GetString()!;
            using var resource=manager.GetResourceSet(CultureInfo.GetCultureInfo(culture),true,false)!;
            Require(resource!=null,"Missing exact resource set: "+culture);
            var actual=resource.Cast<DictionaryEntry>().ToDictionary(p=>(string)p.Key,p=>(string?)p.Value);
            var strings=expected.GetProperty("strings").EnumerateObject().ToDictionary(p=>p.Name,p=>p.Value.GetString());
            Require(actual.Count==strings.Count && strings.All(p=>actual.TryGetValue(p.Key,out var value)&&p.Value==value),"Original resource bytes/values: "+culture);
            sets++;values+=strings.Count;
        }
        Console.WriteLine($"PASS original source Humanizer identity/framework and {sets} resource sets/{values} strings");
        var library=context.LoadFromAssemblyPath(Path.Combine(consumer,"StandardHumanizerConsumer.dll"));
        Console.WriteLine(library.GetType("StandardHumanizerConsumer",true)!.GetMethod("Run")!.Invoke(null,null));
        int declarations=ApiGate.CompareSource("Humanizer",settings.GetProperty("original_source_paths").EnumerateArray().Select(p=>p.GetString()!),settings.GetProperty("defines").EnumerateArray().Select(p=>p.GetString()!),assembly.Location,settings.GetProperty("reference_paths").EnumerateArray().Select(p=>p.GetString()!));
        File.WriteAllText(args[1],JsonSerializer.Serialize(new {assembly_version=identity.Version.ToString(),public_key_token=Convert.ToHexString(identity.GetPublicKeyToken()!).ToLowerInvariant(),framework="netstandard2.0",original_resource_sets=sets,original_resource_values=values,original_public_protected_api_declarations=declarations,isolated_original_runtime_consumer_passed=true,full_dependency_goal_complete=false},new JsonSerializerOptions{WriteIndented=true})+Environment.NewLine);
        return 0;
    }
}
