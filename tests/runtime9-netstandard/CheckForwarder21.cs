using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Runtime.Loader;
using System.Text.Json;

class Program
{
    static void Require(bool value,string reason) {if(!value)throw new Exception(reason);}
    static string AttributeName(MetadataReader md, CustomAttribute a)
    {
        var h=md.GetMemberReference((MemberReferenceHandle)a.Constructor).Parent;
        var t=md.GetTypeReference((TypeReferenceHandle)h);
        return md.GetString(t.Namespace)+"."+md.GetString(t.Name);
    }
    static int Main(string[] args)
    {
        string path=Path.GetFullPath(args[0]);
        var expected=JsonSerializer.Deserialize<string[]>(File.ReadAllText(args[1]))!;
        Require(expected.Length==10,"Original forwarding declaration count");
        using var pe=new PEReader(File.OpenRead(path));var md=pe.GetMetadataReader();var a=md.GetAssemblyDefinition();
        Require(md.GetString(a.Name)=="Microsoft.Bcl.AsyncInterfaces" && a.Version.ToString()=="9.0.0.0","Identity");
        var attributes=a.GetCustomAttributes().Select(md.GetCustomAttribute).ToArray();
        var tfm=attributes.Single(x=>AttributeName(md,x)=="System.Runtime.Versioning.TargetFrameworkAttribute");
        var blob=md.GetBlobReader(tfm.Value);Require(blob.ReadUInt16()==1 && blob.ReadSerializedString()==".NETStandard,Version=v2.1","Actual source target framework");
        Require(!attributes.Any(x=>AttributeName(md,x)=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"),"Forwarding assembly is runtime loadable");
        Require(md.AssemblyReferences.Count==1,"Only Standard2.1 reference");
        var ar=md.GetAssemblyReference(md.AssemblyReferences.Single());
        Require(md.GetString(ar.Name)=="netstandard" && ar.Version.ToString()=="2.1.0.0","Original Standard2.1 AssemblyRef, no NET8 substitution");
        foreach(var h in md.TypeDefinitions) {
            var d=md.GetTypeDefinition(h);
            Require((d.Attributes&TypeAttributes.VisibilityMask)!=TypeAttributes.Public && (d.Attributes&TypeAttributes.VisibilityMask)!=TypeAttributes.NestedPublic,"No competing public async type definitions");
        }
        string ExportName(ExportedTypeHandle h) {
            var d=md.GetExportedType(h);
            return d.Implementation.Kind==HandleKind.ExportedType?ExportName((ExportedTypeHandle)d.Implementation)+"+"+md.GetString(d.Name):md.GetString(d.Namespace)+"."+md.GetString(d.Name);
        }
        var actual=md.ExportedTypes.Select(ExportName).OrderBy(x=>x).ToArray();
        var expanded=new HashSet<string>();
        void Add(Type type) {expanded.Add(type.FullName!);foreach(var child in type.GetNestedTypes(BindingFlags.Public))Add(child);}
        foreach(var name in expected)Add(Type.GetType(name+", System.Private.CoreLib",true)!);
        Require(actual.SequenceEqual(expanded.OrderBy(x=>x)),"Complete original forwarded type graph");
        var context=new AssemblyLoadContext("OriginalAsyncInterfaces21",isCollectible:true);
        try {
            var assembly=context.LoadFromAssemblyPath(path);
            Require(assembly.Location==path,"Owned forwarder loaded");
            Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="cc7b13ffcd2ddd51","Original public key");
            foreach(string name in expected)Require(assembly.GetType(name,true)==Type.GetType(name+", System.Private.CoreLib",true),"Shared runtime type identity: "+name);
        }finally{context.Unload();}
        Console.WriteLine(JsonSerializer.Serialize(new {original_forwarding_declarations=expected.Length,forwarded_types=actual.Length,actual_target=".NETStandard,Version=v2.1",all_runtime_type_identities_shared=true,owned_forwarder_runtime_load_passed=true,full_dependency_goal_complete=false},new JsonSerializerOptions{WriteIndented=true}));
        return 0;
    }
}
