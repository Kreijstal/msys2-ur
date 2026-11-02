using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;

static class RestoreAttributes
{
    static void Main(string[] args)
    {
        var known = new HashSet<string> { "System.Reflection.AssemblyTitleAttribute", "System.Reflection.AssemblyDescriptionAttribute", "System.Reflection.AssemblyDefaultAliasAttribute", "System.Reflection.AssemblyInformationalVersionAttribute", "System.Reflection.AssemblyDelaySignAttribute", "System.Reflection.AssemblyKeyFileAttribute", "System.Reflection.AssemblyMetadataAttribute", "System.Runtime.CompilerServices.InternalsVisibleToAttribute" };
        string name="System.Threading";
        using var policy = JsonDocument.Parse(File.ReadAllText(args[0]));
        {
            var expected = policy.RootElement.GetProperty(name + ".dll").GetProperty("attributes").EnumerateArray().ToArray();
            using var assembly = AssemblyDefinition.ReadAssembly(args[1]);
            var module = assembly.MainModule;
            if (!assembly.CustomAttributes.Any(a => a.AttributeType.FullName == "System.Runtime.CompilerServices.ReferenceAssemblyAttribute")) throw new Exception("Fresh source reference required");
            var runtime = module.AssemblyReferences.Single(r => r.Name == "System.Runtime");
            foreach (var a in assembly.CustomAttributes.Where(a => known.Contains(a.AttributeType.FullName) || a.AttributeType.FullName == "System.Diagnostics.DebuggableAttribute" && !expected.Any(e => e.GetProperty("type").GetString() == a.AttributeType.FullName)).ToArray()) assembly.CustomAttributes.Remove(a);
            foreach (var row in expected.Where(e => known.Contains(e.GetProperty("type").GetString()!)))
            {
                string fullName = row.GetProperty("type").GetString()!; int dot = fullName.LastIndexOf('.');
                var result = module.TypeSystem.Void; result.Scope = runtime;
                var ctor = new MethodReference(".ctor", result, new TypeReference(fullName[..dot], fullName[(dot + 1)..], module, runtime)) { HasThis = true };
                var attribute = new CustomAttribute(ctor);
                foreach (var value in row.GetProperty("arguments").EnumerateArray())
                {
                    bool boolean = fullName == "System.Reflection.AssemblyDelaySignAttribute";
                    var type = boolean ? module.TypeSystem.Boolean : module.TypeSystem.String; type.Scope = runtime;
                    ctor.Parameters.Add(new ParameterDefinition(type)); attribute.ConstructorArguments.Add(new CustomAttributeArgument(type, boolean ? (object)bool.Parse(value.GetString()!) : value.GetString()));
                }
                assembly.CustomAttributes.Add(attribute);
            }
            assembly.Write(args[2]);
            Console.WriteLine("PASS restored original reference assembly metadata: " + args[2]);
        }
    }
}
