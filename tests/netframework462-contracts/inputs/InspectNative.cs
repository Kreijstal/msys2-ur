using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;
static class Program
{
    static void Main(string[] args)
    {
        using var a=AssemblyDefinition.ReadAssembly(args[0]);var data=new SortedDictionary<string,object>(StringComparer.Ordinal);
        void Visit(TypeDefinition t)
        {
            foreach(var m in t.Methods.Where(m=>m.HasPInvokeInfo))data[m.FullName]=new {module=m.PInvokeInfo.Module.Name,entry=m.PInvokeInfo.EntryPoint,attributes=(int)m.PInvokeInfo.Attributes,preserve_sig=m.IsPreserveSig};
            foreach(var n in t.NestedTypes)Visit(n);
        }
        foreach(var t in a.MainModule.Types)Visit(t);File.WriteAllText(args[1],JsonSerializer.Serialize(data,new JsonSerializerOptions{WriteIndented=true})+"\n");
    }
}
