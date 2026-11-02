using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;
static class Program
{
    static readonly string[] LayoutTypes={"System.Runtime.InteropServices.ComTypes.BINDPTR","System.Runtime.InteropServices.ComTypes.ELEMDESC","System.Runtime.InteropServices.ComTypes.ELEMDESC/DESCUNION","System.Runtime.InteropServices.ComTypes.VARDESC","System.Runtime.InteropServices.ComTypes.VARDESC/DESCUNION"};
    static IEnumerable<TypeDefinition> Types(TypeDefinition type)
    {
        yield return type;foreach(var nested in type.NestedTypes)foreach(var item in Types(nested))yield return item;
    }
    static object Layout(AssemblyDefinition assembly,string name)
    {
        var type=assembly.MainModule.Types.SelectMany(Types).Single(t=>t.FullName==name);
        return new {attributes=type.Attributes.ToString(),packing=type.PackingSize,size=type.ClassSize,fields=type.Fields.Where(f=>f.IsPublic).Select(f=>new {name=f.Name,type=f.FieldType.FullName,offset=f.Offset,isStatic=f.IsStatic}).ToArray()};
    }
    static SortedDictionary<string,string[]> ConditionalAttributes(AssemblyDefinition assembly)
    {
        var result=new SortedDictionary<string,string[]>(StringComparer.Ordinal);
        foreach(var type in assembly.MainModule.Types.SelectMany(Types).Where(t=>t.IsPublic || t.IsNestedPublic))
        {
            var values=type.CustomAttributes.Where(a=>a.AttributeType.FullName=="System.Diagnostics.ConditionalAttribute").Select(a=>(string)a.ConstructorArguments[0].Value).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
            if(values.Length!=0)result["T "+type.FullName]=values;
            foreach(var method in type.Methods.Where(m=>m.IsPublic || m.IsFamily || m.IsFamilyOrAssembly))
            {
                values=method.CustomAttributes.Where(a=>a.AttributeType.FullName=="System.Diagnostics.ConditionalAttribute").Select(a=>(string)a.ConstructorArguments[0].Value).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
                if(values.Length!=0)result["M "+method.FullName]=values;
            }
        }
        return result;
    }
    static void Main(string[] args)
    {
        if(args[0]=="--verify-release-consumer")
        {
            using var assembly=AssemblyDefinition.ReadAssembly(args[1]);
            if(assembly.MainModule.Types.SelectMany(Types).SelectMany(t=>t.Methods).Where(m=>m.HasBody).SelectMany(m=>m.Body.Instructions).Any(i=>i.Operand is MethodReference method && method.DeclaringType.FullName=="System.Diagnostics.Debug"))throw new Exception("Release consumer retained a conditional Debug call");
            Console.WriteLine("PASS Release consumer IL omitted conditional Debug.Fail");return;
        }
        if(args[0]=="--read-conditional-metadata")
        {
            using var assembly=AssemblyDefinition.ReadAssembly(args[1]);File.WriteAllText(args[2],JsonSerializer.Serialize(ConditionalAttributes(assembly))+"\n");return;
        }
        if(args[0]=="--read-layout-metadata")
        {
            using var assembly=AssemblyDefinition.ReadAssembly(args[1]);
            File.WriteAllText(args[2],JsonSerializer.Serialize(LayoutTypes.ToDictionary(name=>name,name=>JsonSerializer.Serialize(Layout(assembly,name))),new JsonSerializerOptions{WriteIndented=true})+"\n");return;
        }
        using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));int total=0;var failures=new List<string>();
        foreach(var item in baseline.RootElement.EnumerateObject())
        {
            int before=failures.Count;
            string filename=item.Name.Contains('/')?item.Name.Split('/')[0]+".dll":item.Name;
            string path=item.Name.Contains('/')?Path.Combine(args[0],item.Name,filename):Path.Combine(args[0],filename);
            var expected=item.Value.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();var actual=Api.Read(path);
            if(!expected.SequenceEqual(actual))
            {
                File.WriteAllLines(path+".missing-api.txt",expected.Except(actual));File.WriteAllLines(path+".extra-api.txt",actual.Except(expected));
                failures.Add(item.Name+" original public metadata mismatch");
            }
            using var assembly=AssemblyDefinition.ReadAssembly(path);
            using(var conditionals=JsonDocument.Parse(File.ReadAllText(args[3])))
            {
                string key=assembly.Name.Name+"/"+assembly.Name.Version;
                var expectedConditionals=JsonSerializer.Deserialize<SortedDictionary<string,string[]>>(conditionals.RootElement.GetProperty(key).GetRawText())!;
                var actualConditionals=ConditionalAttributes(assembly);
                if(actualConditionals.Count!=expectedConditionals.Count || actualConditionals.Any(pair=>!expectedConditionals.TryGetValue(pair.Key,out var values) || !pair.Value.SequenceEqual(values)))failures.Add(item.Name+" original public Conditional attributes mismatch");
            }
            if(assembly.Name.FullName!=item.Value.GetProperty("identity").GetString())failures.Add(item.Name+" original identity mismatch");
            if(!assembly.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"))failures.Add(item.Name+" must remain reference-only");
            var references=assembly.MainModule.AssemblyReferences.Select(x=>x.FullName).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
            var expectedRefs=item.Value.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
            if(!references.SequenceEqual(expectedRefs))
            {
                File.WriteAllLines(path+".actual-references.txt",references);File.WriteAllLines(path+".expected-references.txt",expectedRefs);
                failures.Add(item.Name+" original reference identities mismatch");
            }
            if(filename=="System.Runtime.InteropServices.dll")
            {
                using var layouts=JsonDocument.Parse(File.ReadAllText(args[2]));
                foreach(var layout in layouts.RootElement.EnumerateObject())if(JsonSerializer.Serialize(Layout(assembly,layout.Name))!=layout.Value.GetString())failures.Add(item.Name+" original COM layout/field offsets: "+layout.Name);
            }
            total+=expected.Length;Console.WriteLine($"{(before==failures.Count?"PASS":"FAIL")} {item.Name}: {expected.Length} original API entries, identity, reference-only marker and dependency identities");
        }
        if(failures.Count!=0)throw new Exception(string.Join("; ",failures));
        Console.WriteLine($"PASS {baseline.RootElement.EnumerateObject().Count()} source contracts; {total} original API entries");
    }
}
