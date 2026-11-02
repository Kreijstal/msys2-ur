using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Text;
using System.Text.Json;
// Read metadata only. Never load a target assembly into an execution context.
class Program
{
 static void Main(string[] args)
 {
  using var input=File.OpenRead(args[0]);using var pe=new PEReader(input);var reader=pe.GetMetadataReader();
  string TypeName(EntityHandle handle)=>handle.Kind switch {
   HandleKind.TypeReference=>Name(reader.GetTypeReference((TypeReferenceHandle)handle).Namespace,reader.GetTypeReference((TypeReferenceHandle)handle).Name),
   HandleKind.TypeDefinition=>Name(reader.GetTypeDefinition((TypeDefinitionHandle)handle).Namespace,reader.GetTypeDefinition((TypeDefinitionHandle)handle).Name),
   _=>handle.Kind.ToString()};
  string Name(StringHandle ns,StringHandle name)=>reader.GetString(ns)+"."+reader.GetString(name);
  string AttributeName(CustomAttributeHandle handle)
  {
   var ctor=reader.GetCustomAttribute(handle).Constructor;
   return ctor.Kind==HandleKind.MemberReference?TypeName(reader.GetMemberReference((MemberReferenceHandle)ctor).Parent):TypeName(reader.GetMethodDefinition((MethodDefinitionHandle)ctor).GetDeclaringType());
  }
  var analyzers=new SortedSet<string>();var fixes=new SortedSet<string>();var ids=new SortedDictionary<string,string>();
  foreach(var handle in reader.TypeDefinitions)
  {
   var type=reader.GetTypeDefinition(handle);string name=TypeName(handle);
   var attributes=type.GetCustomAttributes().Select(AttributeName).ToArray();
   if(attributes.Contains("Microsoft.CodeAnalysis.Diagnostics.DiagnosticAnalyzerAttribute"))analyzers.Add(name);
   if(attributes.Contains("Microsoft.CodeAnalysis.CodeFixes.ExportCodeFixProviderAttribute"))fixes.Add(name);
   foreach(var fieldHandle in type.GetFields())
   {
    var field=reader.GetFieldDefinition(fieldHandle);if((!reader.GetString(type.Name).EndsWith("DiagnosticIds",StringComparison.Ordinal)&&reader.GetString(field.Name)!="DiagnosticId"&&!reader.GetString(field.Name).EndsWith("RuleId",StringComparison.Ordinal))||field.GetDefaultValue().IsNil)continue;
    var constant=reader.GetConstant(field.GetDefaultValue());if(constant.TypeCode==ConstantTypeCode.String)ids[name+"."+reader.GetString(field.Name)]=Encoding.Unicode.GetString(reader.GetBlobBytes(constant.Value));
   }
  }
  var resources=reader.ManifestResources.Select(h=>reader.GetString(reader.GetManifestResource(h).Name)).OrderBy(n=>n).ToArray();
  Console.WriteLine(JsonSerializer.Serialize(new{analyzers=analyzers.ToArray(),code_fixes=fixes.ToArray(),diagnostic_ids=ids,resources},new JsonSerializerOptions{WriteIndented=true}));
 }
}
