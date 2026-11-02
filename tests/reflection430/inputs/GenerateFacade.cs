// Generate forwarding source from source-built contract and framework references.
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using Mono.Cecil;

static class GenerateFacade
{
    static void Main(string[] args)
    {
        using var contract = AssemblyDefinition.ReadAssembly(args[0]);
        using var seed = AssemblyDefinition.ReadAssembly(args[1]);
        if (seed.Name.FullName != "mscorlib, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089") throw new Exception("Original Framework scope");
        if (!contract.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute") ||
            !seed.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute")) throw new Exception("Source compiler references required");
        var types = contract.MainModule.Types.Where(t => t.IsPublic).OrderBy(t => t.FullName, StringComparer.Ordinal).ToArray();
        if (types.Length != 34 || types.Any(t => t.HasGenericParameters || t.HasNestedTypes)) throw new Exception("Review facade type set");
        foreach (var type in types)
            if (seed.MainModule.GetType(type.FullName) is not { IsPublic: true }) throw new Exception("Missing source Framework type: " + type.FullName);
        using var policy = JsonDocument.Parse(File.ReadAllText(args[2]));
        var attributes = policy.RootElement.GetProperty("System.Reflection.dll").GetProperty("attributes");
        var text = new StringBuilder("// Generated from source contract types and source Framework seed.\n");
        text.AppendLine("[assembly: global::System.Reflection.AssemblyVersion(\"4.1.1.0\")]");
        foreach (var row in attributes.EnumerateArray())
        {
            string name = row.GetProperty("type").GetString()!;
            if (name is "System.Runtime.CompilerServices.CompilationRelaxationsAttribute" or "System.Runtime.CompilerServices.RuntimeCompatibilityAttribute" or "System.Diagnostics.DebuggableAttribute") continue;
            var values = row.GetProperty("arguments").EnumerateArray().Select(v => name == "System.CLSCompliantAttribute" ? v.GetString()!.ToLowerInvariant() : JsonSerializer.Serialize(v.GetString()));
            text.AppendLine("[assembly: global::" + name + "(" + string.Join(", ", values) + ")]");
        }
        foreach (var type in types) text.AppendLine("[assembly: global::System.Runtime.CompilerServices.TypeForwardedTo(typeof(global::" + type.FullName + "))]");
        File.WriteAllText(args[3], text.ToString());
        Console.WriteLine("PASS generated 34 original facade forwards from source contract; every target exists in source Framework mscorlib");
    }
}
