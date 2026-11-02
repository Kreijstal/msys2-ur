using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.InteropServices;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text.Json;
using System.Threading.Tasks;

internal static class Program
{
    static void Require(bool ok,string message){if(!ok)throw new Exception(message);}
    sealed class Isolated : AssemblyLoadContext
    {
        readonly string folder;readonly HashSet<string> names;
        public Isolated(string path,IEnumerable<string> assemblies):base("runtime9-netstandard",true){folder=path;names=new HashSet<string>(assemblies);}
        protected override Assembly? Load(AssemblyName name)=>names.Contains(name.Name!)?LoadFromAssemblyPath(Path.Combine(folder,name.Name+".dll")):null;
    }
    unsafe delegate int ReadFile(SafeHandle handle,byte* data,int count,out int read,IntPtr zero);
    static unsafe void CheckNativeRead(Assembly metadata,string file)
    {
        var type=metadata.GetType("Interop+Kernel32",true)!;
        var method=type.GetMethod("ReadFile",BindingFlags.NonPublic|BindingFlags.Static)!;
        var call=(ReadFile)method.CreateDelegate(typeof(ReadFile));
        using var stream=File.OpenRead(file);byte* data=stackalloc byte[2];
        Require(call(stream.SafeFileHandle,data,2,out int count,IntPtr.Zero)!=0 && count==2 && data[0]=='M' && data[1]=='Z',"Original generated native ReadFile wrapper");
        Console.WriteLine("PASS original source9 generator's native ReadFile wrapper on a real file handle");
    }
    public static async Task<int> Main(string[] args)
    {
        string root=args[0],outDir=args[1],consumer=args[2],config=args[3];
        using var manifest=JsonDocument.Parse(File.ReadAllText(Path.Combine(outDir,"source-inputs.json")));
        using var settings=JsonDocument.Parse(File.ReadAllText(config));
        using var localizations=JsonDocument.Parse(File.ReadAllText(Path.Combine(outDir,"localization.json")));
        string[] names=manifest.RootElement.GetProperty("order").EnumerateArray().Select(x=>x.GetString()!).ToArray();
        string[] maintenance=settings.RootElement.GetProperty("maintenance_names").EnumerateArray().Select(x=>x.GetString()!).ToArray();
        var context=new Isolated(consumer,names.Concat(maintenance).Append("Runtime9Consumer"));
        var assemblies=new Dictionary<string,Assembly>();
        foreach(string name in names)
        {
            Assembly assembly=context.LoadFromAssemblyPath(Path.Combine(consumer,name+".dll"));var record=manifest.RootElement.GetProperty("projects").GetProperty(name);
            Require(assembly.GetName().Version==new Version(9,0,0,0),"Version: "+name);
            Require(Path.GetFullPath(assembly.Location)==Path.GetFullPath(Path.Combine(consumer,name+".dll")),"Source location: "+name);
            byte[] key=File.ReadAllBytes(Path.Combine(outDir,record.GetProperty("key").GetString()+".pubkey"));
            Require(assembly.GetName().GetPublicKey()!.SequenceEqual(key),"Public key: "+name);
            Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion=="9.0.0+9d5a6a9aa463d6d10b0b0ba6d5982cc82f363dc3","Source revision: "+name);
            Require(assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName==".NETStandard,Version=v2.0","Original shipping target: "+name);
            Require((assembly.GetCustomAttribute<CLSCompliantAttribute>()?.IsCompliant==true)==record.GetProperty("cls_compliant").GetBoolean(),"Original CLS override: "+name);
            Require(assembly.GetCustomAttribute<AssemblyDefaultAliasAttribute>()?.DefaultAlias==name,"Original default alias: "+name);
            var flags=assembly.GetCustomAttribute<DefaultDllImportSearchPathsAttribute>()?.Paths;
            Require(flags==(DllImportSearchPath.AssemblyDirectory|DllImportSearchPath.System32),"Original DLL search policy: "+name);
            var attributes=assembly.GetCustomAttributes<AssemblyMetadataAttribute>().ToDictionary(a=>a.Key,a=>a.Value);
            Require(attributes.TryGetValue("PreferInbox",out var inbox) && inbox=="True" && attributes.TryGetValue("Serviceable",out var serviceable) && serviceable=="True","Original inbox/serviceable policy: "+name);
            assemblies.Add(name,assembly);
        }
        int sets=0,values=0;
        foreach(var item in localizations.RootElement.EnumerateArray())
        {
            string name=item.GetProperty("assembly").GetString()!;if(name.StartsWith("bootstrap:",StringComparison.Ordinal)||name.StartsWith("baseline:",StringComparison.Ordinal))continue;
            var manager=new ResourceManager(item.GetProperty("logical_name").GetString()!,assemblies[name]);
            Require(assemblies[name].GetCustomAttribute<NeutralResourcesLanguageAttribute>()?.CultureName=="en-US","Original neutral resource language: "+name);
            string culture=item.GetProperty("culture").GetString()!;
            using var resource=manager.GetResourceSet(CultureInfo.GetCultureInfo(culture),true,false)!;
            Require(resource!=null,"Missing source resource: "+name+"/"+culture);
            var actual=new Dictionary<string,string?>();foreach(DictionaryEntry pair in resource)actual.Add((string)pair.Key,(string?)pair.Value);
            var expected=item.GetProperty("strings").EnumerateObject().ToDictionary(x=>x.Name,x=>x.Value.GetString());
            Require(actual.Count==expected.Count && expected.All(x=>actual.TryGetValue(x.Key,out var value)&&value==x.Value),"Original resource values: "+name);
            sets++;values+=expected.Count;
        }
        Console.WriteLine($"PASS eleven exact netstandard2.0 source assemblies, keys/revisions and {sets} original resource sets/{values} strings");
        using(var stream=assemblies["System.Text.Encoding.CodePages"].GetManifestResourceStream("codepages.nlp")!)
        using(var memory=new MemoryStream())
        {
            stream.CopyTo(memory);string hash=Convert.ToHexString(SHA256.HashData(memory.ToArray())).ToLowerInvariant();
            Require(hash==settings.RootElement.GetProperty("codepages_data_sha256").GetString(),"Complete original codepages.nlp bytes");
        }
        CheckNativeRead(assemblies["System.Reflection.Metadata"],Path.Combine(consumer,"System.Reflection.Metadata.dll"));
        var library=context.LoadFromAssemblyPath(Path.Combine(consumer,"Runtime9Consumer.dll"));
        Console.WriteLine(await (Task<string>)library.GetType("Runtime9Consumer",true)!.GetMethod("Run")!.Invoke(null,new object[]{Path.Combine(consumer,"System.Reflection.Metadata.dll")})!);
        var references=settings.RootElement.GetProperty("standard_reference_paths").EnumerateArray().Select(x=>x.GetString()!).ToArray();
        var all=references.Concat(names.Concat(maintenance).Select(n=>Path.Combine(consumer,n+".dll"))).ToArray();
        var apiCounts=new Dictionary<string,int>();
        foreach(var entry in settings.RootElement.GetProperty("api_baselines").EnumerateObject())
        {
            if(entry.Value.TryGetProperty("metadata",out var metadata))
                apiCounts[entry.Name]=ApiGate.CompareMetadata(entry.Name,metadata.GetString()!,Path.Combine(consumer,entry.Name+".dll"),settings.RootElement.GetProperty("net8_baseline_reference_paths").EnumerateArray().Select(x=>x.GetString()!),all);
            else
                apiCounts[entry.Name]=ApiGate.CompareSource(entry.Name,entry.Value.GetProperty("sources").EnumerateArray().Select(x=>x.GetString()!),entry.Value.GetProperty("defines").EnumerateArray().Select(x=>x.GetString()!),Path.Combine(consumer,entry.Name+".dll"),all);
        }
        File.WriteAllText(args[4],JsonSerializer.Serialize(new {source_assemblies=11,shipping_target="netstandard2.0",original_resource_sets=sets,original_resource_values=values,complete_original_codepages_data_preserved=true,original_generated_native_readfile_passed=true,isolated_original_runtime_checks_passed=true,original_public_api_counts=apiCounts,full_dependency_goal_complete=false},new JsonSerializerOptions{WriteIndented=true})+Environment.NewLine);
        return 0;
    }
}
