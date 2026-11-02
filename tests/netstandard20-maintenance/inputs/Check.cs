using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Resources;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text.Json;
using System.Threading.Tasks;
using System.Xml.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

internal static class Program
{
    static void Require(bool ok,string message) { if(!ok) throw new Exception(message); }
    sealed class Isolated : AssemblyLoadContext
    {
        readonly string directory; readonly HashSet<string> names;
        public Isolated(string path,IEnumerable<string> assemblies):base("source-maintenance",true) { directory=path; names=new HashSet<string>(assemblies); }
        protected override Assembly? Load(AssemblyName name) => names.Contains(name.Name!) ? LoadFromAssemblyPath(Path.Combine(directory,name.Name+".dll")) : null;
    }
    public static async Task<int> Main(string[] args)
    {
        string root=args[0],output=args[1];
        using var manifest=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"source-inputs.json")));
        var records=manifest.RootElement.GetProperty("projects");
        string[] names=records.EnumerateObject().Select(p=>p.Name).ToArray();
        using var resources=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"resources.json")));
        var context=new Isolated(output,names.Append("MaintenanceConsumer"));
        var assemblies=new Dictionary<string,Assembly>();
        foreach(string name in names)
        {
            var record=records.GetProperty(name); var assembly=context.LoadFromAssemblyPath(Path.Combine(output,name+".dll"));
            var identity=assembly.GetName();
            Require(identity.Name==name && identity.Version!.ToString()==record.GetProperty("assembly_version").GetString(),"Identity: "+name);
            Require(Path.GetFullPath(assembly.Location)==Path.GetFullPath(Path.Combine(output,name+".dll")),"Source output location: "+name);
            byte[] key=File.ReadAllBytes(Path.Combine(root,record.GetProperty("key").GetString()+".pubkey"));
            Require(identity.GetPublicKey()!.SequenceEqual(key),"Public key: "+name);
            Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version==record.GetProperty("version").GetString()+".0","Managed file version: "+name);
            Require(FileVersionInfo.GetVersionInfo(assembly.Location).FileVersion==record.GetProperty("version").GetString()+".0","Native file version: "+name);
            Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion==record.GetProperty("version").GetString()+"+"+record.GetProperty("commit").GetString(),"Source commit version: "+name);
            using var pe=new PEReader(File.OpenRead(assembly.Location));
            var md=pe.GetMetadataReader(); Require(md.MetadataVersion.StartsWith("v4.0.30319",StringComparison.Ordinal),"Metadata version: "+name);
            assemblies.Add(name,assembly);
        }
        int values=0,sets=0;
        foreach(var record in resources.RootElement.EnumerateArray())
        {
            var assembly=assemblies[record.GetProperty("assembly").GetString()!];
            var manager=new ResourceManager(record.GetProperty("logical_name").GetString()!,assembly);
            foreach(var item in record.GetProperty("strings").EnumerateObject()) { Require(manager.GetString(item.Name,CultureInfo.InvariantCulture)==item.Value.GetString(),"Original resource: "+assembly.GetName().Name+"/"+item.Name); values++; }
            sets++;
        }
        Console.WriteLine($"PASS exact source assembly locations, identities, keys, native/managed versions and {sets} resource sets/{values} strings");
        var references=Directory.GetFiles(Path.Combine(root,"..","netstandard20-2","ref"),"*.dll").Concat(names.Select(n=>Path.Combine(output,n+".dll"))).Select(p=>MetadataReference.CreateFromFile(p));
        var compilation=CSharpCompilation.Create("MaintenanceApiAudit",references:references,options:new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary,metadataImportOptions:MetadataImportOptions.All));
        var apiCounts=new Dictionary<string,object>();
        foreach(string name in names)
        {
            var record=records.GetProperty(name);
            string xml=Path.Combine(root,"maintenance-packages-"+record.GetProperty("commit").GetString(),"src",name,"src",name+".xml");
            int count=0,publicCount=0;
            foreach(var member in XDocument.Load(xml).Descendants("member"))
            {
                string id=member.Attribute("name")!.Value;
                var symbol=DocumentationCommentId.GetFirstSymbolForDeclarationId(id,compilation);
                Require(symbol!=null && symbol.ContainingAssembly.Identity.Name==name,"Original documented API missing or rebound: "+name+"/"+id);
                if(symbol!.DeclaredAccessibility==Accessibility.Public || symbol.DeclaredAccessibility==Accessibility.Protected || symbol.DeclaredAccessibility==Accessibility.ProtectedOrInternal) publicCount++;
                count++;
            }
            apiCounts.Add(name,new {original_documented_declarations=count,public_or_protected=publicCount,other_documented_declarations=count-publicCount});
            Console.WriteLine($"PASS {name}: all {count} original documented declarations ({publicCount} public/protected)");
        }
        int unsafeMethods=assemblies["System.Runtime.CompilerServices.Unsafe"].GetType("System.Runtime.CompilerServices.Unsafe",true)!.GetMethods(BindingFlags.Public|BindingFlags.Static|BindingFlags.DeclaredOnly).Length;
        Require(unsafeMethods==42,"Original Unsafe public method count");
        var consumer=context.LoadFromAssemblyPath(Path.Combine(output,"MaintenanceConsumer.dll"));
        var task=(Task<string>)consumer.GetType("MaintenanceConsumer",true)!.GetMethod("Run")!.Invoke(null,null)!;
        string message=await task;Console.WriteLine(message);
        Require(context.Assemblies.All(a=>a.ManifestModule.Name!="Framework.dll"),"Unexpected Framework implementation module");
        string report=JsonSerializer.Serialize(new {source_assemblies=5,all_source_locations_identities_versions_keys_verified=true,original_resource_sets=sets,original_resource_values=values,documented_api_counts=apiCounts,unsafe_public_methods=unsafeMethods,isolated_source_runtime_consumer_passed=true,full_dependency_goal_complete=false},new JsonSerializerOptions {WriteIndented=true});
        File.WriteAllText(args[2],report+Environment.NewLine);
        return 0;
    }
}
