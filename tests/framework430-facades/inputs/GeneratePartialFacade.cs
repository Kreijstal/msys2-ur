using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using Mono.Cecil;

static class GeneratePartialFacade
{
    static string CSharp(string name)
    {
        int tick = name.IndexOf('`');
        return "global::" + (tick < 0 ? name : name[..tick] + "<" + new string(',', int.Parse(name[(tick + 1)..]) - 1) + ">");
    }
    static void Main(string[] args)
    {
        using var contract = AssemblyDefinition.ReadAssembly(args[0]);
        using var baseline = JsonDocument.Parse(File.ReadAllText(args[1]));
        using var exports = JsonDocument.Parse(File.ReadAllText(args[2]));
        var seeds = args.Skip(4).Select(p => AssemblyDefinition.ReadAssembly(p)).ToArray();
        try
        {
            if (!contract.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute") || seeds.Any(s => !s.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute"))) throw new Exception("Source references required");
            var expected = baseline.RootElement.GetProperty(contract.Name.Name + ".dll");
            var rows = exports.RootElement[0].GetProperty("exported_types").EnumerateArray().Where(e => e.GetProperty("declaring_type").ValueKind == JsonValueKind.Null).ToArray();
            var owned = contract.Name.Name switch {
                "System.Diagnostics.Tracing" => new[] { "System.Diagnostics.Tracing.EventCounter" },
                "System.Net.Sockets" => new[] { "System.Net.Sockets.SocketTaskExtensions", "System.Net.Sockets.SocketReceiveFromResult", "System.Net.Sockets.SocketReceiveMessageFromResult" },
                _ => Array.Empty<string>() };
            var types = contract.MainModule.Types.Where(t => t.IsPublic).Select(t => t.FullName).Except(owned).OrderBy(n => n, StringComparer.Ordinal).ToArray();
            if (!types.SequenceEqual(rows.Select(e => e.GetProperty("full_name").GetString()!).OrderBy(n => n, StringComparer.Ordinal))) throw new Exception("Original source facade type set: " + contract.Name.Name);
            foreach (var row in rows)
            {
                string name = row.GetProperty("full_name").GetString()!;
                var seed = seeds.Single(s => s.MainModule.GetType(name) is { IsPublic: true });
                if (seed.Name.FullName != row.GetProperty("scope").GetString()) throw new Exception("Original source target scope: " + name);
            }
            var identity = new AssemblyNameReference("unused", new Version(0, 0));
            identity = AssemblyNameReference.Parse(expected.GetProperty("identity").GetString()!);
            var text = new StringBuilder("// Generated from source reference declarations and verified source Framework targets.\n[assembly:global::System.Reflection.AssemblyVersion(\"" + identity.Version + "\")]\n");
            foreach (var row in expected.GetProperty("attributes").EnumerateArray())
            {
                string name = row.GetProperty("type").GetString()!;
                if (name is "System.Runtime.CompilerServices.CompilationRelaxationsAttribute" or "System.Runtime.CompilerServices.RuntimeCompatibilityAttribute" or "System.Diagnostics.DebuggableAttribute" or "System.Runtime.CompilerServices.ExtensionAttribute") continue;
                var values = row.GetProperty("arguments").EnumerateArray().Select(v => name == "System.CLSCompliantAttribute" ? v.GetString()!.ToLowerInvariant() : JsonSerializer.Serialize(v.GetString()));
                text.AppendLine("[assembly:global::" + name + "(" + string.Join(", ", values) + ")]");
            }
            foreach (var name in types) text.AppendLine("[assembly:global::System.Runtime.CompilerServices.TypeForwardedTo(typeof(" + CSharp(name) + "))]");
            File.WriteAllText(args[3], text.ToString());
            Console.WriteLine("PASS original source facade type set and Framework scopes: " + contract.Name.Name + " " + types.Length + " top-level forwards; " + owned.Length + " source implementation types");
        }
        finally { foreach (var seed in seeds) seed.Dispose(); }
    }
}
