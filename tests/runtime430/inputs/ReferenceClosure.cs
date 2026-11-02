// Find same-assembly declaration dependencies; read metadata, never method bodies.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;

static class ReferenceClosure
{
    static void Main(string[] args)
    {
        using var assembly = AssemblyDefinition.ReadAssembly(args[0]);
        var module = assembly.MainModule;
        var all = module.GetTypes().ToDictionary(t => t.FullName);
        var needed = new HashSet<string>(JsonSerializer.Deserialize<string[]>(File.ReadAllText(args[1]))!);
        var pending = new Queue<string>(needed);
        void Add(TypeReference? reference)
        {
            if (reference == null) return;
            if (reference is GenericInstanceType generic) foreach (var arg in generic.GenericArguments) Add(arg);
            if (reference is TypeSpecification specification) { Add(specification.ElementType); return; }
            if (all.ContainsKey(reference.FullName) && needed.Add(reference.FullName)) pending.Enqueue(reference.FullName);
        }
        void Attributes(ICustomAttributeProvider provider)
        {
            foreach (var a in provider.CustomAttributes)
            {
                Add(a.AttributeType);
                foreach (var v in a.ConstructorArguments) { Add(v.Type); if (v.Value is TypeReference t) Add(t); }
                foreach (var v in a.Properties) { Add(v.Argument.Type); if (v.Argument.Value is TypeReference t) Add(t); }
                foreach (var v in a.Fields) { Add(v.Argument.Type); if (v.Argument.Value is TypeReference t) Add(t); }
            }
        }
        while (pending.Count != 0)
        {
            var type = all[pending.Dequeue()]; Add(type.BaseType); Attributes(type);
            if (type.IsNested) Add(type.DeclaringType);
            foreach (var nested in type.NestedTypes.Where(t => t.IsNestedPublic || t.IsNestedFamily || t.IsNestedFamilyOrAssembly)) Add(nested);
            foreach (var i in type.Interfaces) Add(i.InterfaceType);
            foreach (var g in type.GenericParameters) { Attributes(g); foreach (var c in g.Constraints) Add(c.ConstraintType); }
            foreach (var field in type.Fields.Where(f => f.IsPublic || f.IsFamily || f.IsFamilyOrAssembly)) { Add(field.FieldType); Attributes(field); }
            foreach (var method in type.Methods.Where(m => m.IsPublic || m.IsFamily || m.IsFamilyOrAssembly))
            {
                Add(method.ReturnType); Attributes(method); Attributes(method.MethodReturnType);
                foreach (var p in method.Parameters) { Add(p.ParameterType); Attributes(p); }
                foreach (var g in method.GenericParameters) { Attributes(g); foreach (var c in g.Constraints) Add(c.ConstraintType); }
            }
            foreach (var p in type.Properties) if (p.GetMethod is { IsPublic: true } || p.SetMethod is { IsPublic: true }) Attributes(p);
            foreach (var e in type.Events) if (e.AddMethod is { IsPublic: true }) { Add(e.EventType); Attributes(e); }
        }
        File.WriteAllText(args[2], JsonSerializer.Serialize(needed.OrderBy(n => n, StringComparer.Ordinal), new JsonSerializerOptions { WriteIndented = true }) + "\n");
        Console.WriteLine("PASS original declaration dependency closure: " + needed.Count + " types");
    }
}
