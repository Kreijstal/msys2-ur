using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;

// Reads the newly compiled shim as data. Target names must remain the historical
// public facade identities, including the Syndication assembly.
using var pe=new PEReader(File.OpenRead(args[0]));
var reader=pe.GetMetadataReader();
var assembly=reader.GetAssemblyDefinition();
if(reader.GetString(assembly.Name)!="System.ServiceModel" || assembly.Version!=new Version(4,0,0,0))throw new Exception("legacy identity");
string token=Convert.ToHexString(SHA1.HashData(reader.GetBlobBytes(assembly.PublicKey)).TakeLast(8).Reverse().ToArray()).ToLowerInvariant();
if(token!="b77a5c561934e089" || reader.MethodDefinitions.Count!=0)throw new Exception("legacy key/methods");
string Name(ExportedTypeHandle handle) {
    var type=reader.GetExportedType(handle);
    return type.Implementation.Kind==HandleKind.ExportedType
        ?Name((ExportedTypeHandle)type.Implementation)+"+"+reader.GetString(type.Name)
        :(reader.GetString(type.Namespace)+"."+reader.GetString(type.Name)).TrimStart('.');
}
AssemblyReference Target(EntityHandle handle) => handle.Kind==HandleKind.ExportedType
    ?Target(reader.GetExportedType((ExportedTypeHandle)handle).Implementation)
    :reader.GetAssemblyReference((AssemblyReferenceHandle)handle);
using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));
var wanted=baseline.RootElement.GetProperty("forwards").EnumerateArray().ToDictionary(e=>e.GetProperty("type").GetString(),e=>e.GetProperty("target").GetString());
var got=new Dictionary<string,string>();
foreach(var handle in reader.ExportedTypes) {
    var target=Target(reader.GetExportedType(handle).Implementation);
    string name=reader.GetString(target.Name);
    var version=name=="System.ServiceModel.Syndication"?new Version(8,0,0,0):new Version(4,10,3,0);
    if(target.Version!=version)throw new Exception("forward target version: "+name);
    got.Add(Name(handle),name);
}
if(got.Count!=274 || wanted.Count!=got.Count || wanted.Any(e=>!got.TryGetValue(e.Key,out var value)||value!=e.Value))throw new Exception("legacy forwarding table differs");
Console.WriteLine("PASS legacy System.ServiceModel 4.0.0.0/b77a5c561934e089: 274 exact forwards, original facade targets, zero methods");
