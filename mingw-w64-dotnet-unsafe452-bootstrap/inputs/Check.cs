using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
using Mono.Cecil;
using Mono.Cecil.Cil;
sealed class OwnedContext:AssemblyLoadContext
{
    readonly string folder;
    public OwnedContext(string folder):base(isCollectible:true){this.folder=folder;}
    protected override Assembly? Load(AssemblyName name)=>name.Name=="System.Runtime.CompilerServices.Unsafe"?LoadFromAssemblyPath(Path.Combine(folder,name.Name+".dll")):null;
}
static class Program
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static object BodyOperand(object? value,Mono.Collections.Generic.Collection<Instruction> instructions)=>value switch
    {
        null=>"",Instruction instruction=>"@"+instructions.IndexOf(instruction),Instruction[] list=>string.Join(",",list.Select(x=>instructions.IndexOf(x))),
        MethodReference method=>method.FullName,TypeReference type=>type.FullName,FieldReference field=>field.FullName,
        ParameterDefinition parameter=>"arg"+parameter.Index,VariableDefinition variable=>"var"+variable.Index,
        _=>Convert.ToString(value,CultureInfo.InvariantCulture)??""
    };
    static SortedDictionary<string,string[]> Bodies(string path)
    {
        using var assembly=AssemblyDefinition.ReadAssembly(path);var result=new SortedDictionary<string,string[]>(StringComparer.Ordinal);
        foreach(var method in assembly.MainModule.Types.Where(t=>t.IsPublic).SelectMany(t=>t.Methods).Where(m=>m.IsPublic && m.HasBody))
            result[method.FullName]=method.Body.Instructions.Select(i=>i.OpCode.Code+" "+BodyOperand(i.Operand,method.Body.Instructions)).ToArray();
        return result;
    }
    static void Main(string[] args)
    {
        if(args[0]=="--bodies"){File.WriteAllText(args[2],JsonSerializer.Serialize(Bodies(args[1]),new JsonSerializerOptions{WriteIndented=true})+"\n");return;}
        string file=Path.GetFullPath(args[0]);using var baseline=JsonDocument.Parse(File.ReadAllText(args[1]));var expected=baseline.RootElement.GetProperty("System.Runtime.CompilerServices.Unsafe.dll");
        var wanted=expected.GetProperty("api").EnumerateArray().Select(x=>x.GetString()!).ToArray();var actual=Api.Read(file);
        File.WriteAllLines(file+".missing-api.txt",wanted.Except(actual));File.WriteAllLines(file+".extra-api.txt",actual.Except(wanted));Require(wanted.SequenceEqual(actual),"Original Unsafe public API");
        using(var assembly=AssemblyDefinition.ReadAssembly(file))
        {
            Require(assembly.Name.FullName==expected.GetProperty("identity").GetString(),"Original identity");
            Require(assembly.MainModule.AssemblyReferences.Select(x=>x.FullName).SequenceEqual(expected.GetProperty("references").EnumerateArray().Select(x=>x.GetString()!)),"Original dependency identities");
            bool reference=args[2]=="--reference";
            Require(assembly.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute")==reference,"Reference/runtime distinction");
            foreach(var attribute in expected.GetProperty("attributes").EnumerateArray())
            {
                string type=attribute.GetProperty("type").GetString()!;
                if(!type.StartsWith("System.Reflection.",StringComparison.Ordinal) && type!="System.Security.AllowPartiallyTrustedCallersAttribute")continue;
                var values=attribute.GetProperty("arguments").EnumerateArray().Select(x=>x.GetString()).ToArray();
                Require(assembly.CustomAttributes.Any(a=>a.AttributeType.FullName==type && a.ConstructorArguments.Select(x=>Convert.ToString(x.Value,CultureInfo.InvariantCulture)).SequenceEqual(values)),"Original managed attribute "+type);
            }
        }
        using var policy=JsonDocument.Parse(File.ReadAllText(args[3]));var native=FileVersionInfo.GetVersionInfo(file);
        foreach(var property in policy.RootElement.GetProperty("native_VERSIONINFO").EnumerateObject())
        {
            var member=typeof(FileVersionInfo).GetProperty(property.Name)!;var value=member.GetValue(native);
            Require(value is bool boolean ? boolean==property.Value.GetBoolean() : value is int number ? number==property.Value.GetInt32() : (string?)value==property.Value.GetString(),"Original native VERSIONINFO "+property.Name);
        }
        if(args[2]=="--reference"){Console.WriteLine("PASS original reference35 API/identity/dependencies/reference marker and native version metadata");return;}
        var expectedBodies=JsonSerializer.Deserialize<Dictionary<string,string[]>>(File.ReadAllText(args[2]))!;var actualBodies=Bodies(file);
        Require(expectedBodies.Count==actualBodies.Count && expectedBodies.All(p=>actualBodies.TryGetValue(p.Key,out var body) && p.Value.SequenceEqual(body)),"Original public IL method bodies");
        string folder=Path.GetDirectoryName(file)!;var context=new OwnedContext(folder);var bridge=context.LoadFromAssemblyPath(Path.Combine(folder,"Bridge.dll"));
        Console.WriteLine(bridge.GetType("Bridge")!.GetMethod("Run")!.Invoke(null,null));
        Require(context.Assemblies.Single(a=>a.GetName().Name=="System.Runtime.CompilerServices.Unsafe").Location==file,"Must execute exact original-version candidate");
        context.Unload();Console.WriteLine("PASS 35 original API entries, exact IL bodies/identity/dependencies and original native VERSIONINFO");
    }
}
