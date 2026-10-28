// Read PE metadata and resource bytes only; never load target code.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Resources;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

class Program
{
 static void Main(string[] args)
 {
  using var input=File.OpenRead(args[0]);using var pe=new PEReader(input);var metadata=pe.GetMetadataReader();
  var assembly=metadata.GetAssemblyDefinition();
  string Token(byte[] publicKey)=>Convert.ToHexString(SHA1.HashData(publicKey).TakeLast(8).Reverse().ToArray()).ToLowerInvariant();
  var resources=new SortedDictionary<string,object>();
  var directory=pe.PEHeaders.CorHeader.ResourcesDirectory;
  var section=pe.GetSectionData(directory.RelativeVirtualAddress).GetContent().ToArray();
  foreach(var handle in metadata.ManifestResources)
  {
   var resource=metadata.GetManifestResource(handle);if(!resource.Implementation.IsNil)throw new Exception("External resource");
   string name=metadata.GetString(resource.Name);int offset=checked((int)resource.Offset);int length=BitConverter.ToInt32(section,offset);byte[] data=section.AsSpan(offset+4,length).ToArray();
   if(name.EndsWith(".resources"))
   {
    var strings=new SortedDictionary<string,string>();using var reader=new ResourceReader(new MemoryStream(data));
    foreach(DictionaryEntry entry in reader){if(entry.Value is not string text)throw new Exception("Nonstring resource "+entry.Key);strings[(string)entry.Key]=text;}
    resources[name]=strings;
   }
   else resources[name]=new{sha256=Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant(),length};
  }
  var versions=new SortedDictionary<string,string>();
  foreach(var h in assembly.GetCustomAttributes())
  {
   var a=metadata.GetCustomAttribute(h);if(a.Constructor.Kind!=HandleKind.MemberReference)continue;
   var ctor=metadata.GetMemberReference((MemberReferenceHandle)a.Constructor);if(ctor.Parent.Kind!=HandleKind.TypeReference)continue;
   var type=metadata.GetTypeReference((TypeReferenceHandle)ctor.Parent);string name=metadata.GetString(type.Name);
   if(name is "AssemblyFileVersionAttribute" or "AssemblyInformationalVersionAttribute")
   {
    var blob=metadata.GetBlobReader(a.Value);if(blob.ReadUInt16()!=1)throw new Exception("Attribute prolog");versions[name]=blob.ReadSerializedString();
   }
  }
  var references=metadata.AssemblyReferences.Select(h=>metadata.GetAssemblyReference(h)).Select(r=>new{name=metadata.GetString(r.Name),version=r.Version.ToString()}).OrderBy(r=>r.name).ToArray();
  Console.WriteLine(JsonSerializer.Serialize(new{name=metadata.GetString(assembly.Name),version=assembly.Version.ToString(),culture=metadata.GetString(assembly.Culture),public_key_token=Token(metadata.GetBlobBytes(assembly.PublicKey)),versions,references,resources},new JsonSerializerOptions{WriteIndented=true}));
 }
}
