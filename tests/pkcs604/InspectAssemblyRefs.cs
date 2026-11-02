using System;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;

internal static class Program
{
    static int Main(string[] args)
    {
        var records = args.Select(path => {
            using var pe = new PEReader(File.OpenRead(path));
            var md = pe.GetMetadataReader();
            var assembly = md.GetAssemblyDefinition();
            return new { path, name = md.GetString(assembly.Name), version = assembly.Version.ToString(),
                sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant(),
                references = md.AssemblyReferences.Select(h => { var r = md.GetAssemblyReference(h);
                    return new { name = md.GetString(r.Name), version = r.Version.ToString() }; }).ToArray() };
        }).ToArray();
        Console.WriteLine(JsonSerializer.Serialize(records, new JsonSerializerOptions { WriteIndented = true }));
        return 0;
    }
}
