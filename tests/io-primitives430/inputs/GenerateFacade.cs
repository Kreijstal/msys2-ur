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
        var types = contract.MainModule.Types.Where(t => t.IsPublic).Select(t => t.FullName).Concat(contract.MainModule.ExportedTypes.Select(t => t.FullName)).Distinct().OrderBy(t => t, StringComparer.Ordinal).ToArray();
        if (types.Length != 16 || types.Any(t => t.Contains("`") || t.Contains("/"))) throw new Exception("Review facade type set");
        using var systemSeed = AssemblyDefinition.ReadAssembly(args[4]);
        if (systemSeed.Name.FullName != "System, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089" ||
            !systemSeed.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute")) throw new Exception("Selected source System reference");
        using var systemPolicy = JsonDocument.Parse(File.ReadAllText(args[5]));
        var expectedAPI = systemPolicy.RootElement.GetProperty("selected_type_API").EnumerateArray().Select(v => v.GetString()!).ToArray();
        if (!Api.Read(args[4]).SequenceEqual(expectedAPI)) throw new Exception("Selected System exception API and declaration flags");
        foreach (var type in types)
        {
            var target = type == "System.IO.InvalidDataException" ? systemSeed : seed;
            if (target.MainModule.GetType(type) is not { IsPublic: true }) throw new Exception("Missing source Framework type: " + type);
        }
        using var policy = JsonDocument.Parse(File.ReadAllText(args[2]));
        var attributes = policy.RootElement.GetProperty("System.IO.dll").GetProperty("attributes");
        var text = new StringBuilder("// Generated from source contract types and source Framework seed.\n");
        text.AppendLine("[assembly: global::System.Reflection.AssemblyVersion(\"4.1.1.0\")]");
        foreach (var row in attributes.EnumerateArray())
        {
            string name = row.GetProperty("type").GetString()!;
            if (name is "System.Runtime.CompilerServices.CompilationRelaxationsAttribute" or "System.Runtime.CompilerServices.RuntimeCompatibilityAttribute" or "System.Diagnostics.DebuggableAttribute") continue;
            var values = row.GetProperty("arguments").EnumerateArray().Select(v => name == "System.CLSCompliantAttribute" ? v.GetString()!.ToLowerInvariant() : JsonSerializer.Serialize(v.GetString()));
            text.AppendLine("[assembly: global::" + name + "(" + string.Join(", ", values) + ")]");
        }
        foreach (var type in types) text.AppendLine("[assembly: global::System.Runtime.CompilerServices.TypeForwardedTo(typeof(global::" + type + "))]");
        File.WriteAllText(args[3], text.ToString());
        Console.WriteLine("PASS generated 16 original facade forwards from source contract; every target exists in source Framework mscorlib/selected System contracts");
    }
}
