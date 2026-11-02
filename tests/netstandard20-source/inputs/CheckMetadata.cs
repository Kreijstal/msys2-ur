using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;

internal static class Program
{
    static string AttributeName(MetadataReader md, CustomAttribute ca)
    {
        EntityHandle h = ca.Constructor.Kind == HandleKind.MemberReference
            ? md.GetMemberReference((MemberReferenceHandle)ca.Constructor).Parent
            : md.GetMethodDefinition((MethodDefinitionHandle)ca.Constructor).GetDeclaringType();
        if (h.Kind == HandleKind.TypeReference) { var t=md.GetTypeReference((TypeReferenceHandle)h); return md.GetString(t.Namespace)+"."+md.GetString(t.Name); }
        var d=md.GetTypeDefinition((TypeDefinitionHandle)h); return md.GetString(d.Namespace)+"."+md.GetString(d.Name);
    }
    static void Require(bool ok,string why) { if(!ok) throw new Exception(why); }
    public static int Main(string[] args)
    {
        string root=args[0];
        using var doc=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"build-results.json")));
        using var forwardDoc=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"expected-forwards.json")));
        var identities=new Dictionary<string,(Version version, byte[] token)>();
        var references=new List<(string owner,string name,Version version,byte[] token)>();
        var results=new Dictionary<string,object>();
        var nested=new Dictionary<string,List<string>>();
        foreach(string path in new[]{Path.Combine(root,"ref","netstandard.dll")}.Concat(Directory.GetFiles(Path.Combine(root,"extensions"),"*.dll")))
        {
            using var pe=new PEReader(File.OpenRead(path)); var md=pe.GetMetadataReader();
            string TypeName(TypeDefinitionHandle h) { var d=md.GetTypeDefinition(h); return d.GetDeclaringType().IsNil ? md.GetString(d.Namespace)+"."+md.GetString(d.Name) : TypeName(d.GetDeclaringType())+"+"+md.GetString(d.Name); }
            foreach(var h in md.TypeDefinitions) { var d=md.GetTypeDefinition(h); var children=d.GetNestedTypes().Select(TypeName).ToList(); if(children.Count>0) nested.Add(TypeName(h),children); }
        }
        int allForwards=0,contractTypes=0,contractMethods=0;
        foreach(var entry in doc.RootElement.EnumerateObject())
        {
            string name=entry.Name;
            string path=Path.Combine(root,entry.Value.GetProperty("package_asset").GetBoolean()?"ref":"extensions",name+".dll");
            using var pe=new PEReader(File.OpenRead(path)); var md=pe.GetMetadataReader(); var a=md.GetAssemblyDefinition();
            Require(md.GetString(a.Name)==name && a.Version.ToString()==entry.Value.GetProperty("assembly_version").GetString(),"Identity: "+name);
            byte[] key=md.GetBlobBytes(a.PublicKey), expected=File.ReadAllBytes(Path.Combine(root,entry.Value.GetProperty("key").GetString()+".pubkey"));
            Require(key.SequenceEqual(expected),"Key: "+name);
            byte[] token=SHA1.HashData(key).TakeLast(8).Reverse().ToArray(); identities.Add(name,(a.Version,token));
            Require(a.GetCustomAttributes().Any(h=>AttributeName(md,md.GetCustomAttribute(h))=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"),"Reference marker: "+name);
            foreach(var h in md.AssemblyReferences) { var r=md.GetAssemblyReference(h); references.Add((name,md.GetString(r.Name),r.Version,md.GetBlobBytes(r.PublicKeyOrToken))); }
            string ExportName(ExportedTypeHandle h) { var t=md.GetExportedType(h); return t.Implementation.Kind==HandleKind.ExportedType ? ExportName((ExportedTypeHandle)t.Implementation)+"+"+md.GetString(t.Name) : md.GetString(t.Namespace)+"."+md.GetString(t.Name); }
            var forwards=md.ExportedTypes.Select(ExportName).OrderBy(x=>x).ToArray();
            var expanded=new List<string>();
            void Expand(string type) { expanded.Add(type); if(nested.TryGetValue(type,out var children)) foreach(string child in children) Expand(child); }
            foreach(var f in forwardDoc.RootElement.GetProperty(name).EnumerateArray()) Expand(f.GetString()!);
            var expectedForwards=expanded.OrderBy(x=>x).ToArray();
            Require(forwards.SequenceEqual(expectedForwards),"Original forwards: "+name+" missing=["+string.Join(",",expectedForwards.Except(forwards))+"] extra=["+string.Join(",",forwards.Except(expectedForwards))+"]");
            allForwards+=forwards.Length;
            if(name=="netstandard") { Require(md.AssemblyReferences.Count==0,"Core reference must be self-contained"); contractTypes=md.TypeDefinitions.Count; contractMethods=md.MethodDefinitions.Count; }
            results.Add(name,new { version=a.Version.ToString(),token=Convert.ToHexString(token).ToLowerInvariant(),types=md.TypeDefinitions.Count,methods=md.MethodDefinitions.Count,forwarded_types=forwards.Length });
        }
        foreach(var r in references) { Require(identities.TryGetValue(r.name,out var target),"Unresolved reference: "+r.owner+" -> "+r.name); Require(r.version==target.version && r.token.SequenceEqual(target.token),"Reference identity: "+r.owner+" -> "+r.name); }
        Require(results.Count==117,"Incomplete source graph");
        Console.WriteLine(JsonSerializer.Serialize(new { assemblies=117,package_assets=113,original_forwarded_types=allForwards,contract_types=contractTypes,contract_methods=contractMethods,all_identities_keys_markers_dependencies_original_forwards_verified=true,results },new JsonSerializerOptions {WriteIndented=true}));
        return 0;
    }
}
