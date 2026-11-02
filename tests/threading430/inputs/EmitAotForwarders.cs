// Source port of the original metadata-only facade. No provider implementation is emitted.
using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;

static class Program
{
    static void Main(string[] args)
    {
        using var assembly=AssemblyDefinition.ReadAssembly(args[0]);
        using var policy=JsonDocument.Parse(File.ReadAllText(args[1]));
        var module=assembly.MainModule;
        if(module.ExportedTypes.Count!=0||module.Types.Any(t=>t.Name!="<Module>"))throw new Exception("Source-compiled empty facade required");
        if(assembly.Name.FullName!="System.Threading, Version=4.0.12.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a")throw new Exception("Original identity required");
        foreach(var row in policy.RootElement[0].GetProperty("exported_types").EnumerateArray())
        {
            if(!row.GetProperty("is_forwarder").GetBoolean()||row.GetProperty("declaring_type").ValueKind!=JsonValueKind.Null)throw new Exception("Review unsupported forwarder row");
            string scopeName=row.GetProperty("scope").GetString()!;
            var scope=module.AssemblyReferences.SingleOrDefault(r=>r.FullName==scopeName);
            if(scope==null)
            {
                scope=AssemblyNameReference.Parse(scopeName);
                if(scope.Name!="System.Private.CoreLib.Threading"&&scope.Name!="System.Private.Threading")throw new Exception("Original private scope required");
                module.AssemblyReferences.Add(scope);
            }
            string name=row.GetProperty("full_name").GetString()!;int dot=name.LastIndexOf('.');
            module.ExportedTypes.Add(new ExportedType(name[..dot],name[(dot+1)..],module,scope){Attributes=(TypeAttributes)row.GetProperty("attributes").GetInt32()});
        }
        if(module.ExportedTypes.Count!=31||module.AssemblyReferences.Count!=3)throw new Exception("Original31 forwarders and3 assembly references required");
        assembly.Write(args[2]);
        Console.WriteLine("PASS source AOT facade metadata port:31 original forwarders; private provider execution remains unverified");
    }
}
