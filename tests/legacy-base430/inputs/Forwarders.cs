// Read original PE metadata with source Cecil; never load inspected assemblies.
using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using Mono.Cecil;

static class Program
{
    static void Main(string[] args)
    {
        var records = args.Skip(1).Select(path =>
        {
            using var assembly = AssemblyDefinition.ReadAssembly(path);
            return new
            {
                file = path,
                sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant(),
                identity = assembly.Name.FullName,
                reference_only = assembly.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute"),
                assembly_references = assembly.MainModule.AssemblyReferences.Select(r => r.FullName).OrderBy(s => s, StringComparer.Ordinal).ToArray(),
                exported_types = assembly.MainModule.ExportedTypes.Select(t => new
                {
                    full_name = t.FullName,
                    attributes = (uint)t.Attributes,
                    is_forwarder = t.IsForwarder,
                    scope = t.Scope.ToString(),
                    declaring_type = t.DeclaringType?.FullName
                }).OrderBy(t => t.full_name, StringComparer.Ordinal).ToArray()
            };
        }).ToArray();
        File.WriteAllText(args[0], JsonSerializer.Serialize(records, new JsonSerializerOptions { WriteIndented = true }) + "\n");
    }
}
