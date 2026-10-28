// Metadata only: do not load or execute the inspected implementation.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;

using var pe=new PEReader(File.OpenRead(args[0]));
var reader=pe.GetMetadataReader();var assembly=reader.GetAssemblyDefinition();
var attributes=new Dictionary<string,string>();
int? debuggableFlags=null;
foreach(var handle in assembly.GetCustomAttributes())
{
    var attribute=reader.GetCustomAttribute(handle);
    if(attribute.Constructor.Kind!=HandleKind.MemberReference)continue;
    var constructor=reader.GetMemberReference((MemberReferenceHandle)attribute.Constructor);
    if(constructor.Parent.Kind!=HandleKind.TypeReference)continue;
    var type=reader.GetTypeReference((TypeReferenceHandle)constructor.Parent);
    string name=reader.GetString(type.Name);
    if(name=="DebuggableAttribute") {
        var debug=reader.GetBlobReader(attribute.Value);if(debug.ReadUInt16()!=1)throw new Exception("debug attribute prolog");
        debuggableFlags=debug.ReadInt32();continue;
    }
    if(name is not ("AssemblyFileVersionAttribute" or "AssemblyInformationalVersionAttribute"))continue;
    var blob=reader.GetBlobReader(attribute.Value);if(blob.ReadUInt16()!=1)throw new Exception("attribute prolog");
    attributes[name]=blob.ReadSerializedString();
}
var types=new SortedDictionary<string,string[]>();
foreach(var handle in reader.TypeDefinitions)
{
    var type=reader.GetTypeDefinition(handle);string name=reader.GetString(type.Namespace)+"."+reader.GetString(type.Name);
    types[name]=type.GetMethods().Select(h=>reader.GetMethodDefinition(h)).Select(m=>reader.GetString(m.Name)+" flags="+m.Attributes).ToArray();
}
var exported=reader.ExportedTypes.Select(h=>{
    var type=reader.GetExportedType(h);
    if(type.Implementation.Kind!=HandleKind.AssemblyReference)throw new Exception("unexpected exported-type implementation");
    var target=reader.GetAssemblyReference((AssemblyReferenceHandle)type.Implementation);
    return new {name=reader.GetString(type.Namespace)+"."+reader.GetString(type.Name),
        is_forwarder=type.IsForwarder,target_assembly=reader.GetString(target.Name),target_version=target.Version.ToString()};
}).OrderBy(t=>t.name).ToArray();
var key=reader.GetBlobBytes(assembly.PublicKey);
Console.WriteLine(JsonSerializer.Serialize(new{
    name=reader.GetString(assembly.Name),version=assembly.Version.ToString(),
    public_key_token=key.Length==0?"null":Convert.ToHexString(SHA1.HashData(key).TakeLast(8).Reverse().ToArray()).ToLowerInvariant(),
    attributes,types,exported_types=exported,debuggable_flags=debuggableFlags
},new JsonSerializerOptions{WriteIndented=true}));
