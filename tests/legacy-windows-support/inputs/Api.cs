using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;

static class Api
{
    internal static readonly string[] Names={"Mono.Cecil","Mono.Cecil.Rocks","Mono.Cecil.Mdb","Mono.Cecil.Pdb"};
    static string Constant(object? value) => value==null ? "null" : value is string text ? JsonSerializer.Serialize(text) : Convert.ToString(value,CultureInfo.InvariantCulture)!;
    static string Parameter(ParameterDefinition p) => p.Name+":"+p.ParameterType.FullName+":"+p.Attributes+":"+(p.HasConstant?Constant(p.Constant):"<none>");
    static string Generic(GenericParameter p) => p.Name+":"+p.Attributes+":"+string.Join(",",p.Constraints.Select(c=>c.ConstraintType.FullName));
    static bool Visible(MethodDefinition m) => m.IsPublic||m.IsFamily||m.IsFamilyOrAssembly;
    static bool Visible(FieldDefinition f) => f.IsPublic||f.IsFamily||f.IsFamilyOrAssembly;
    internal static string[] Read(string path)
    {
        using var assembly=AssemblyDefinition.ReadAssembly(path,new ReaderParameters{ReadingMode=ReadingMode.Deferred});
        var entries=new SortedSet<string>(StringComparer.Ordinal);
        void Visit(TypeDefinition type)
        {
            entries.Add("T "+type.FullName+"|"+type.Attributes+"|base="+type.BaseType?.FullName+"|interfaces="+string.Join(",",type.Interfaces.Select(i=>i.InterfaceType.FullName).OrderBy(n=>n,StringComparer.Ordinal))+"|generic="+string.Join(";",type.GenericParameters.Select(Generic)));
            foreach(var m in type.Methods.Where(Visible))
                entries.Add("M "+m.FullName+"|"+m.Attributes+"|impl="+m.ImplAttributes+"|parameters="+string.Join(";",m.Parameters.Select(Parameter))+"|generic="+string.Join(";",m.GenericParameters.Select(Generic)));
            foreach(var f in type.Fields.Where(Visible))
                entries.Add("F "+f.FullName+"|"+f.Attributes+"|constant="+(f.HasConstant?Constant(f.Constant):"<none>"));
            foreach(var p in type.Properties.Where(p=>(p.GetMethod!=null&&Visible(p.GetMethod))||(p.SetMethod!=null&&Visible(p.SetMethod))))
                entries.Add("P "+p.FullName+"|"+p.Attributes);
            foreach(var e in type.Events.Where(e=>e.AddMethod!=null&&Visible(e.AddMethod)))
                entries.Add("E "+e.FullName+"|"+e.Attributes);
            foreach(var nested in type.NestedTypes.Where(t=>t.IsNestedPublic||t.IsNestedFamily||t.IsNestedFamilyOrAssembly))Visit(nested);
        }
        foreach(var type in assembly.MainModule.Types.Where(t=>t.IsPublic))Visit(type);
        return entries.ToArray();
    }
    internal static void Dump(string directory,string output)
    {
        var values=Names.ToDictionary(n=>n,n=>Read(Path.Combine(directory,n+".dll")));
        File.WriteAllText(output,JsonSerializer.Serialize(values,new JsonSerializerOptions{WriteIndented=true})+"\n");
    }
    internal static void Check(string baseline)
    {
        var expected=JsonSerializer.Deserialize<Dictionary<string,string[]>>(File.ReadAllText(baseline))!;
        int count=0;
        foreach(var name in Names)
        {
            var actual=Read(Path.Combine(AppContext.BaseDirectory,name+".dll"));
            var missing=expected[name].Except(actual).ToArray();var extra=actual.Except(expected[name]).ToArray();
            if(missing.Length!=0||extra.Length!=0)throw new Exception(name+": missing="+missing.Length+", extra="+extra.Length+"\n"+string.Join("\n",missing.Take(10))+"\n"+string.Join("\n",extra.Take(10)));
            count+=actual.Length;
        }
        Console.WriteLine("PASS all four original published NS2 API inventories: "+count+" declarations; zero differences");
    }
}
