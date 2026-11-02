// Restore known assembly metadata omitted by the reference-source snapshot.
// All attribute constructors are definitions in the freshly compiled core contract.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;

static class RestoreReferenceAttributes
{
    static void Main(string[] args)
    {
        var known = new HashSet<string> {
            "System.Reflection.AssemblyTitleAttribute", "System.Reflection.AssemblyDescriptionAttribute",
            "System.Reflection.AssemblyDefaultAliasAttribute", "System.Reflection.AssemblyInformationalVersionAttribute",
            "System.Reflection.AssemblyDelaySignAttribute", "System.Reflection.AssemblyKeyFileAttribute",
            "System.Reflection.AssemblyMetadataAttribute", "System.Runtime.CompilerServices.InternalsVisibleToAttribute"
        };
        foreach (var tfm in new[] { "netstandard1.0", "netstandard1.2", "netstandard1.3", "netstandard1.5" })
        {
            using var policy = JsonDocument.Parse(File.ReadAllText(Path.Combine(args[0], "System.Runtime-" + tfm + ".json")));
            var expected = policy.RootElement.GetProperty("System.Runtime.dll").GetProperty("attributes").EnumerateArray().ToArray();
            using var assembly = AssemblyDefinition.ReadAssembly(Path.Combine(args[1], "System.Runtime", tfm, "System.Runtime.dll"));
            if (assembly.MainModule.AssemblyReferences.Count != 0 || !assembly.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute")) throw new Exception("Fresh self-contained source core reference required");
            foreach (var a in assembly.CustomAttributes.Where(a => known.Contains(a.AttributeType.FullName) ||
                a.AttributeType.FullName == "System.Diagnostics.DebuggableAttribute" && !expected.Any(e => e.GetProperty("type").GetString() == a.AttributeType.FullName)).ToArray()) assembly.CustomAttributes.Remove(a);
            foreach (var row in expected.Where(e => known.Contains(e.GetProperty("type").GetString()!)))
            {
                string name = row.GetProperty("type").GetString()!;
                var values = row.GetProperty("arguments").EnumerateArray().ToArray();
                var type = assembly.MainModule.GetType(name) ?? throw new Exception("Missing source attribute declaration: " + name);
                var ctor = type.Methods.Single(m => m.IsConstructor && !m.IsStatic && m.Parameters.Count == values.Length && m.Parameters.All(p => p.ParameterType.FullName is "System.String" or "System.Boolean"));
                var attribute = new CustomAttribute(ctor);
                for (int i = 0; i < values.Length; i++)
                {
                    string value = values[i].GetString()!;
                    attribute.ConstructorArguments.Add(new CustomAttributeArgument(ctor.Parameters[i].ParameterType, ctor.Parameters[i].ParameterType.FullName == "System.Boolean" ? (object)bool.Parse(value) : value));
                }
                assembly.CustomAttributes.Add(attribute);
            }
            string folder = Path.Combine(args[2], "System.Runtime", tfm); Directory.CreateDirectory(folder);
            assembly.Write(Path.Combine(folder, "System.Runtime.dll"));
            Console.WriteLine("PASS restored original Runtime assembly metadata without external assembly references: " + tfm);
        }
    }
}
