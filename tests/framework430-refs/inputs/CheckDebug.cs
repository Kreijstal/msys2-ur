using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;

static class Program
{
    static void Main(string[] args)
    {
        if (args[0] == "--consumer")
        {
            using var consumer = AssemblyDefinition.ReadAssembly(args[1]);
            if (consumer.MainModule.Types.SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions).Any(i => i.Operand is MethodReference m && m.DeclaringType.FullName == "System.Diagnostics.Debug")) throw new Exception("Release Debug call retained");
            Console.WriteLine("PASS original Conditional semantics omit Debug calls from Release consumer IL"); return;
        }
        using var policy = JsonDocument.Parse(File.ReadAllText(args[0]));
        foreach (string path in args.Skip(1))
        {
            using var assembly = AssemblyDefinition.ReadAssembly(path);
            string key = assembly.Name.Name + "/" + assembly.Name.Version;
            var actual = assembly.MainModule.Types.SelectMany(t => t.Methods).Where(m => m.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Diagnostics.ConditionalAttribute"))
                .ToDictionary(m => "M " + m.ReturnType.FullName + " " + m.DeclaringType.FullName + "::" + m.Name + "(" + string.Join(",", m.Parameters.Select(p => p.ParameterType.FullName)) + ")", m => m.CustomAttributes.Where(a => a.AttributeType.FullName == "System.Diagnostics.ConditionalAttribute").Select(a => (string)a.ConstructorArguments[0].Value).ToArray());
            var expected = policy.RootElement.GetProperty(key);
            if (actual.Count != expected.EnumerateObject().Count()) throw new Exception("Conditional count: " + key);
            foreach (var row in expected.EnumerateObject())
                if (!actual.TryGetValue(row.Name, out var values) || !values.SequenceEqual(row.Value.EnumerateArray().Select(v => v.GetString()!))) throw new Exception("Original Conditional attribute: " + row.Name);
            Console.WriteLine("PASS original Debug conditional calls: " + key + " entries=" + actual.Count);
        }
    }
}
