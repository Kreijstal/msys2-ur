// Modern csc forwards every public nested seed type. Original GenFacades used
// the contract's type set; remove only the four verified extra nested rows.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;

static class PortFacadeExports
{
    static void Main(string[] args)
    {
        using var assembly = AssemblyDefinition.ReadAssembly(args[0]);
        using var policy = JsonDocument.Parse(File.ReadAllText(args[1]));
        var expected = policy.RootElement.GetProperty("exported_types").EnumerateArray().Select(e => e.GetProperty("full_name").GetString()!).ToHashSet();
        var extras = assembly.MainModule.ExportedTypes.Where(t => !expected.Contains(t.FullName)).ToArray();
        var known = new HashSet<string> { "System.TimeZoneInfo/AdjustmentRule", "System.TimeZoneInfo/TransitionTime", "System.Runtime.CompilerServices.RuntimeHelpers/CleanupCode", "System.Runtime.CompilerServices.RuntimeHelpers/TryCode" };
        if (assembly.Name.Name != "System.Runtime" || assembly.MainModule.Types.Any(t => t.Name != "<Module>") || extras.Length != 4 || !known.SetEquals(extras.Select(t => t.FullName)) || extras.Any(t => t.DeclaringType == null)) throw new Exception("Unexpected source facade export set");
        foreach (var type in extras) assembly.MainModule.ExportedTypes.Remove(type);
        if (assembly.MainModule.ExportedTypes.Count != 277 || !expected.SetEquals(assembly.MainModule.ExportedTypes.Select(t => t.FullName))) throw new Exception("Original facade exports");
        assembly.Write(args[2]);
        Console.WriteLine("PASS source facade contract projection removed exactly four extra nested seed exports; all277 original exports retained");
    }
}
