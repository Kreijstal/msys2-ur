// Inspect exported MEF implementation identities and exact attribute blobs as metadata only.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Text.Json;
class Program
{
 static void Main(string[] args)
 {
  using var stream=File.OpenRead(args[0]);using var pe=new PEReader(stream);var m=pe.GetMetadataReader();
  string TypeName(EntityHandle handle)
  {
   if(handle.Kind==HandleKind.TypeDefinition)
   {
    var t=m.GetTypeDefinition((TypeDefinitionHandle)handle);var parent=t.GetDeclaringType();
    return parent.IsNil?(m.GetString(t.Namespace)+"."+m.GetString(t.Name)).TrimStart('.'):TypeName(parent)+"+"+m.GetString(t.Name);
   }
   if(handle.Kind==HandleKind.TypeReference)
   {
    var t=m.GetTypeReference((TypeReferenceHandle)handle);
    return t.ResolutionScope.Kind==HandleKind.TypeReference?TypeName(t.ResolutionScope)+"+"+m.GetString(t.Name):(m.GetString(t.Namespace)+"."+m.GetString(t.Name)).TrimStart('.');
   }
   throw new Exception("Unexpected type handle "+handle.Kind);
  }
  var bases=new Dictionary<string,string>();
  foreach(string dependency in new[]{args[0],Path.Combine(Path.GetDirectoryName(Path.GetFullPath(args[0])),"Microsoft.CodeAnalysis.Workspaces.dll")})
  {
   using var dependencyStream=File.OpenRead(dependency);using var dependencyPe=new PEReader(dependencyStream);var reader=dependencyPe.GetMetadataReader();
   string Name(EntityHandle handle)
   {
    if(handle.Kind==HandleKind.TypeReference){var t=reader.GetTypeReference((TypeReferenceHandle)handle);return (reader.GetString(t.Namespace)+"."+reader.GetString(t.Name)).TrimStart('.');}
    var d=reader.GetTypeDefinition((TypeDefinitionHandle)handle);return (reader.GetString(d.Namespace)+"."+reader.GetString(d.Name)).TrimStart('.');
   }
   foreach(var h in reader.TypeDefinitions)
   {
    var d=reader.GetTypeDefinition(h);
    if(d.BaseType.Kind is HandleKind.TypeDefinition or HandleKind.TypeReference&&!d.BaseType.IsNil)bases[Name(h)]=Name(d.BaseType);
   }
  }
  bool IsExport(string name)
  {
   var seen=new HashSet<string>();
   while(seen.Add(name)){if(name=="System.Composition.ExportAttribute")return true;if(!bases.TryGetValue(name,out name))return false;}
   throw new Exception("Attribute inheritance cycle");
  }
  var exports=new SortedDictionary<string,SortedDictionary<string,string>>();
  foreach(var h in m.TypeDefinitions)
  {
   var type=m.GetTypeDefinition(h);var attributes=new SortedDictionary<string,string>();
   foreach(var ah in type.GetCustomAttributes())
   {
    var a=m.GetCustomAttribute(ah);var declaring=a.Constructor.Kind==HandleKind.MemberReference?m.GetMemberReference((MemberReferenceHandle)a.Constructor).Parent:m.GetMethodDefinition((MethodDefinitionHandle)a.Constructor).GetDeclaringType();
    string name=TypeName(declaring);
    if(IsExport(name))
    {
     // Multiple exports of the same attribute type remain distinct records.
     string key=name;int index=1;while(attributes.ContainsKey(key))key=name+"#"+(index++);
     attributes.Add(key,Convert.ToHexString(m.GetBlobBytes(a.Value)).ToLowerInvariant());
    }
   }
   if(attributes.Count!=0)exports.Add(TypeName(h),attributes);
  }
  Console.WriteLine(JsonSerializer.Serialize(exports,new JsonSerializerOptions{WriteIndented=true}));
 }
}
