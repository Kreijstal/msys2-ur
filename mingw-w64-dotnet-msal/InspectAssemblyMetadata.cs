// Read PE metadata only; never load the inspected implementation assembly.
using System;
using System.Buffers.Binary;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Resources;
using System.Security.Cryptography;
using System.Text.Json;

var results = new List<object>();
foreach (string path in args)
{
    using var pe = new PEReader(File.OpenRead(path));
    var reader = pe.GetMetadataReader();
    var assembly = reader.GetAssemblyDefinition();
    var attributes = new SortedDictionary<string, string>();
    var assembly_metadata = new SortedDictionary<string, string>();
    foreach (var handle in assembly.GetCustomAttributes())
    {
        var attribute = reader.GetCustomAttribute(handle);
        if (attribute.Constructor.Kind != HandleKind.MemberReference) continue;
        var constructor = reader.GetMemberReference((MemberReferenceHandle)attribute.Constructor);
        if (constructor.Parent.Kind != HandleKind.TypeReference) continue;
        var type = reader.GetTypeReference((TypeReferenceHandle)constructor.Parent);
        string name = reader.GetString(type.Name);
        if(name=="AssemblyMetadataAttribute") { var metadata=reader.GetBlobReader(attribute.Value); if(metadata.ReadUInt16()!=1)throw new Exception("Invalid metadata prolog"); assembly_metadata[metadata.ReadSerializedString()]=metadata.ReadSerializedString(); continue; }
        if (name is not ("AssemblyFileVersionAttribute" or "AssemblyInformationalVersionAttribute")) continue;
        var blob = reader.GetBlobReader(attribute.Value);
        if (blob.ReadUInt16() != 1) throw new Exception("Invalid custom attribute prolog");
        attributes[name] = blob.ReadSerializedString();
    }
    byte[] key = reader.GetBlobBytes(assembly.PublicKey);
    var resources = new SortedDictionary<string, SortedDictionary<string, string>>();
    var raw_resources=new SortedDictionary<string, object>();
    foreach (var handle in reader.ManifestResources)
    {
        var resource = reader.GetManifestResource(handle);
        string name = reader.GetString(resource.Name);
        if (!resource.Implementation.IsNil) continue;
        var section = pe.GetSectionData(pe.PEHeaders.CorHeader.ResourcesDirectory.RelativeVirtualAddress);
        int offset = checked((int)resource.Offset);
        int size = BinaryPrimitives.ReadInt32LittleEndian(section.GetContent(offset, 4).AsSpan());
        var raw=section.GetContent(offset+4,size).ToArray();
        raw_resources[name]=new {sha256=Convert.ToHexString(SHA256.HashData(raw)).ToLowerInvariant(),data=Convert.ToBase64String(raw)};
        if (!name.EndsWith(".resources", StringComparison.Ordinal))continue;
        using var stream = new MemoryStream(raw);
        using var resourceReader = new ResourceReader(stream);
        var values = new SortedDictionary<string, string>();
        IDictionaryEnumerator enumerator = resourceReader.GetEnumerator();
        while (enumerator.MoveNext())
        {
            string resourceName = (string)enumerator.Key;
            // GetResourceData returns raw bytes, avoiding deserialization of objects.
            resourceReader.GetResourceData(resourceName, out string type, out byte[] data);
            if (type != "ResourceTypeCode.String") continue;
            using var valueReader = new BinaryReader(new MemoryStream(data));
            values[resourceName] = valueReader.ReadString();
        }
        resources[name] = values;
    }
    results.Add(new {
        file = path, sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant(),
        name = reader.GetString(assembly.Name), version = assembly.Version.ToString(),
        public_key = Convert.ToHexString(key).ToLowerInvariant(),
        public_key_token = key.Length == 0 ? "null" : Convert.ToHexString(SHA1.HashData(key).TakeLast(8).Reverse().ToArray()).ToLowerInvariant(),
        attributes, assembly_metadata, raw_resources, strong_name_signed=pe.PEHeaders.CorHeader.Flags.HasFlag(CorFlags.StrongNameSigned), strong_name_signature_nonzero=pe.PEHeaders.CorHeader.StrongNameSignatureDirectory.Size>0 && pe.GetSectionData(pe.PEHeaders.CorHeader.StrongNameSignatureDirectory.RelativeVirtualAddress).GetContent(0,pe.PEHeaders.CorHeader.StrongNameSignatureDirectory.Size).Any(b=>b!=0), resources, exported_types = reader.ExportedTypes.Count,
        references = reader.AssemblyReferences.Select(handle => {
            var reference = reader.GetAssemblyReference(handle);
            return new { name = reader.GetString(reference.Name), version = reference.Version.ToString(),
                public_key_or_token = Convert.ToHexString(reader.GetBlobBytes(reference.PublicKeyOrToken)).ToLowerInvariant() };
        }).OrderBy(reference => reference.name).ToArray()
    });
}
Console.WriteLine(JsonSerializer.Serialize(results, new JsonSerializerOptions { WriteIndented = true }));
