using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;

internal static class Program
{
    static string AttributeName(MetadataReader md, CustomAttribute a)
    {
        EntityHandle h = a.Constructor.Kind == HandleKind.MemberReference
            ? md.GetMemberReference((MemberReferenceHandle)a.Constructor).Parent
            : md.GetMethodDefinition((MethodDefinitionHandle)a.Constructor).GetDeclaringType();
        if (h.Kind == HandleKind.TypeReference)
        { var t = md.GetTypeReference((TypeReferenceHandle)h); return md.GetString(t.Namespace) + "." + md.GetString(t.Name); }
        var d = md.GetTypeDefinition((TypeDefinitionHandle)h);
        return md.GetString(d.Namespace) + "." + md.GetString(d.Name);
    }
    static int Main(string[] args)
    {
        using var expected = JsonDocument.Parse(File.ReadAllText(args[1]));
        var known = new Dictionary<string, (Version version, string token)>();
        var references = new List<(string owner, string target, Version version, string token)>();
        var results = new Dictionary<string, object>();
        foreach (var p in expected.RootElement.EnumerateObject())
        {
            string path = Path.Combine(args[0], p.Name + ".dll");
            using var pe = new PEReader(File.OpenRead(path));
            var md = pe.GetMetadataReader();
            var a = md.GetAssemblyDefinition();
            if (md.GetString(a.Name) != p.Name || a.Version.ToString() != p.Value.GetProperty("assembly_version").GetString()) throw new Exception("Identity: " + p.Name);
            byte[] key = md.GetBlobBytes(a.PublicKey);
            if (Convert.ToHexString(key).ToLowerInvariant() != p.Value.GetProperty("public_key").GetString()) throw new Exception("Key: " + p.Name);
            string token = Convert.ToHexString(SHA1.HashData(key).TakeLast(8).Reverse().ToArray()).ToLowerInvariant();
            bool marker = false; string? framework = null;
            foreach (var handle in a.GetCustomAttributes())
            {
                var attr = md.GetCustomAttribute(handle);
                string type = AttributeName(md, attr);
                if (type == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute") marker = true;
                if (type == "System.Runtime.Versioning.TargetFrameworkAttribute")
                {
                    var blob = md.GetBlobReader(attr.Value);
                    if (blob.ReadUInt16() != 1) throw new Exception("Attribute prolog");
                    framework = blob.ReadSerializedString();
                }
            }
            if (!marker || ((int)a.Flags & 0x70) != 0x70 || framework != ".NETCoreApp,Version=v6.0") throw new Exception("Reference marker/flags/TFM: " + p.Name + " flags=" + a.Flags);
            string? fileVersion = FileVersionInfo.GetVersionInfo(path).FileVersion;
            if (fileVersion != p.Value.GetProperty("file_version").GetString()) throw new Exception("File version: " + p.Name);
            known.Add(p.Name, (a.Version, token));
            foreach (var handle in md.AssemblyReferences)
            {
                var r = md.GetAssemblyReference(handle);
                references.Add((p.Name, md.GetString(r.Name), r.Version, Convert.ToHexString(md.GetBlobBytes(r.PublicKeyOrToken)).ToLowerInvariant()));
            }
            results.Add(p.Name, new { version = a.Version.ToString(), file_version = fileVersion, token,
                framework, reference_assembly = marker, flags = (int)a.Flags,
                types = md.TypeDefinitions.Count, methods = md.MethodDefinitions.Count, exported_types = md.ExportedTypes.Count,
                sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() });
        }
        foreach (var r in references)
            if (!known.TryGetValue(r.target, out var target) || r.version != target.version || r.token != target.token)
                throw new Exception("Original NET6 reference closure mismatch: " + r.owner + " -> " + r.target + " " + r.version);
        if (results.Count != 137) throw new Exception("Original core graph count");
        Console.WriteLine(JsonSerializer.Serialize(new { core_reference_assemblies = 137,
            all_original_names_versions_keys_file_versions_reference_markers_flags_and_NET6_TFMs_verified = true,
            all_emitted_reference_versions_and_keys_resolve_to_own_NET6_graph = true,
            compatibility_facades_built = false, complete_targeting_pack_built = false,
            full_dependency_goal_complete = false, assemblies = results }, new JsonSerializerOptions { WriteIndented = true }));
        return 0;
    }
}
