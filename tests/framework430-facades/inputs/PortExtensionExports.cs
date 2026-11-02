using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;

static class PortExtensionExports
{
    static void Main(string[] args)
    {
        using var assembly = AssemblyDefinition.ReadAssembly(args[0]);
        using var policy = JsonDocument.Parse(File.ReadAllText(args[1]));
        var expected = policy.RootElement[0].GetProperty("exported_types").EnumerateArray().Select(e => e.GetProperty("full_name").GetString()!).ToHashSet();
        var extras = assembly.MainModule.ExportedTypes.Where(t => !expected.Contains(t.FullName)).ToArray();
        var known = new[] { "System.Environment/SpecialFolder", "System.Environment/SpecialFolderOption" }.ToHashSet();
        if (assembly.Name.Name != "System.Runtime.Extensions" || expected.Count != 13 || extras.Length != 2 || !known.SetEquals(extras.Select(t => t.FullName)) || extras.Any(t => t.DeclaringType?.FullName != "System.Environment" || t.IsForwarder || (int)t.Attributes != 0 || t.Scope.ToString() != "mscorlib, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089")) throw new Exception("Unexpected generated extension export rows");
        foreach (var row in extras) assembly.MainModule.ExportedTypes.Remove(row);
        if (!expected.SetEquals(assembly.MainModule.ExportedTypes.Select(t => t.FullName))) throw new Exception("Original extension export set");
        assembly.Write(args[2]);
        Console.WriteLine("PASS removed exactly two compiler-added Environment nested exports; all 13 original records retained");
    }
}
