using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using Mono.Cecil;

static class GenerateRuntimeFacade
{
    static string CSharp(string name)
    {
        if (name == "System.Void") return "void";
        int tick = name.IndexOf('`');
        return "global::" + (tick < 0 ? name : name[..tick] + "<" + new string(',', int.Parse(name[(tick + 1)..]) - 1) + ">");
    }
    static void Main(string[] args)
    {
        using var contract = AssemblyDefinition.ReadAssembly(args[0]);
        var seeds = args.Skip(4).Select(AssemblyDefinition.ReadAssembly).ToArray();
        try
        {
            foreach (var seed in seeds)
                if (!seed.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute")) throw new Exception("Source reference seed required");
            var names = contract.MainModule.Types.Where(t => t.IsPublic).Select(t => t.FullName).Concat(new[] { "System.Runtime.InteropServices.GCHandle", "System.Runtime.InteropServices.GCHandleType" }).OrderBy(n => n, StringComparer.Ordinal).ToArray();
            if (names.Length != 275 || names.Distinct().Count() != 275) throw new Exception("Complete original top-level facade type set");
            using var forwards = JsonDocument.Parse(File.ReadAllText(args[3]));
            var expected = forwards.RootElement.GetProperty("exported_types").EnumerateArray().Where(e => e.GetProperty("declaring_type").ValueKind == JsonValueKind.Null).ToDictionary(e => e.GetProperty("full_name").GetString()!, e => e.GetProperty("scope").GetString()!);
            if (!names.SequenceEqual(expected.Keys.OrderBy(n => n, StringComparer.Ordinal))) throw new Exception("Original source forward names");
            foreach (var name in names)
            {
                var seed = seeds.Single(s => s.MainModule.GetType(name) is { IsPublic: true });
                if (seed.Name.FullName != expected[name]) throw new Exception("Original forwarding scope: " + name);
            }
            using var attributes = JsonDocument.Parse(File.ReadAllText(args[1]));
            var text = new StringBuilder("// Generated from source Runtime contract and validated source Framework seeds.\n[assembly:global::System.Reflection.AssemblyVersion(\"4.1.1.0\")]\n");
            foreach (var row in attributes.RootElement.GetProperty("System.Runtime.dll").GetProperty("attributes").EnumerateArray())
            {
                string name = row.GetProperty("type").GetString()!;
                if (name is "System.Runtime.CompilerServices.CompilationRelaxationsAttribute" or "System.Runtime.CompilerServices.RuntimeCompatibilityAttribute" or "System.Diagnostics.DebuggableAttribute") continue;
                var values = row.GetProperty("arguments").EnumerateArray().Select(v => name == "System.CLSCompliantAttribute" ? v.GetString()!.ToLowerInvariant() : JsonSerializer.Serialize(v.GetString()));
                text.AppendLine("[assembly:global::" + name + "(" + string.Join(", ", values) + ")]");
            }
            foreach (var name in names) text.AppendLine("[assembly:global::System.Runtime.CompilerServices.TypeForwardedTo(typeof(" + CSharp(name) + "))]");
            File.WriteAllText(args[2], text.ToString());
            Console.WriteLine("PASS generated 275 top-level Runtime forwarding declarations; compiler supplies two nested exports; all source target scopes match");
        }
        finally { foreach (var seed in seeds) seed.Dispose(); }
    }
}
