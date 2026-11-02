// Restore only the two legacy attribute records omitted by SBRP, and remove
// the automatic Debuggable attribute absent from those original references.
// Input assemblies must be freshly source-compiled reference assemblies.
using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;

static class RestoreAttributes
{
    static void Main(string[] args)
    {
        string baselineDirectory = args[0], input = args[1], output = args[2];
        Directory.CreateDirectory(output);
        foreach (string name in new[] { "System.Reflection" })
        {
            using var policy = JsonDocument.Parse(File.ReadAllText(Path.Combine(baselineDirectory, name + "-netstandard1.0.json")));
            var expected = policy.RootElement.GetProperty(name + ".dll").GetProperty("attributes");
            using var assembly = AssemblyDefinition.ReadAssembly(Path.Combine(input, name, "netstandard1.0", name + ".dll"));
            if (!assembly.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute"))
                throw new Exception("A source reference assembly is required");
            if (expected.EnumerateArray().Any(a => a.GetProperty("type").GetString() == "System.Diagnostics.DebuggableAttribute"))
                throw new Exception("Unexpected original Debuggable attribute");
            foreach (var a in assembly.CustomAttributes.Where(a => a.AttributeType.FullName == "System.Diagnostics.DebuggableAttribute").ToArray())
                assembly.CustomAttributes.Remove(a);
            var module = assembly.MainModule;
            var runtime = module.AssemblyReferences.Single(r => r.Name == "System.Runtime" && r.Version == new Version(4, 0, 0, 0));
            foreach (string type in new[] { "AssemblyDelaySignAttribute", "AssemblyKeyFileAttribute" })
            {
                string fullName = "System.Reflection." + type;
                if (assembly.CustomAttributes.Any(a => a.AttributeType.FullName == fullName)) throw new Exception("Unexpected pre-existing legacy attribute");
                var row = expected.EnumerateArray().Single(a => a.GetProperty("type").GetString() == fullName);
                string value = row.GetProperty("arguments")[0].GetString()!;
                bool boolean = type == "AssemblyDelaySignAttribute";
                var parameter = boolean ? module.TypeSystem.Boolean : module.TypeSystem.String;
                parameter.Scope = runtime;
                var resultType = module.TypeSystem.Void;
                resultType.Scope = runtime;
                var constructor = new MethodReference(".ctor", resultType,
                    new TypeReference("System.Reflection", type, module, runtime)) { HasThis = true };
                constructor.Parameters.Add(new ParameterDefinition(parameter));
                var attribute = new CustomAttribute(constructor);
                attribute.ConstructorArguments.Add(new CustomAttributeArgument(parameter, boolean ? (object)bool.Parse(value) : value));
                assembly.CustomAttributes.Add(attribute);
            }
            string folder = Path.Combine(output, name, "netstandard1.0");
            Directory.CreateDirectory(folder);
            assembly.Write(Path.Combine(folder, name + ".dll"));
            Console.WriteLine("PASS source metadata port: " + name + "; original delay-sign/key-file attribute records restored");
        }
        foreach (var item in new[] { ("System.Reflection", "netstandard1.3"), ("System.Reflection", "netstandard1.5") })
        {
            string folder = Path.Combine(output, item.Item1, item.Item2);
            Directory.CreateDirectory(folder);
            File.Copy(Path.Combine(input, item.Item1, item.Item2, item.Item1 + ".dll"), Path.Combine(folder, item.Item1 + ".dll"));
        }
    }
}
