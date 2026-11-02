using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mono.Cecil;
static class SeedMetadata
{
    static HashSet<string>? Selected;
    static bool Visible(MethodDefinition m)=>m.IsPublic||m.IsFamily||m.IsFamilyOrAssembly;
    static bool Visible(FieldDefinition f)=>f.IsPublic||f.IsFamily||f.IsFamilyOrAssembly;
    static IEnumerable<TypeDefinition> Types(ModuleDefinition module)
    {
        IEnumerable<TypeDefinition> Visit(TypeDefinition t){yield return t;foreach(var n in t.NestedTypes.Where(n=>n.IsNestedPublic||n.IsNestedFamily||n.IsNestedFamilyOrAssembly))foreach(var v in Visit(n))yield return v;}
        return module.Types.Where(t=>t.IsPublic && (Selected==null||Selected.Contains(t.FullName))).SelectMany(Visit);
    }
    static object? Marshal(MarshalInfo? info)
    {
        if(info==null)return null;
        var values=new Dictionary<string,object?>();
        foreach(var p in info.GetType().GetProperties())
        {
            object? v=p.GetValue(info);values[p.Name]=v is Enum?Convert.ToInt32(v):v is TypeReference t?t.FullName:v;
        }
        return new {kind=info.GetType().Name,values};
    }
    static object Security(ISecurityDeclarationProvider provider)=>provider.SecurityDeclarations.Select(d=>new {action=(int)d.Action,blob=Convert.ToBase64String(d.GetBlob())}).ToArray();
    static void Record(string input,string output)
    {
        using var assembly=AssemblyDefinition.ReadAssembly(input);var result=new SortedDictionary<string,object>(StringComparer.Ordinal);
        foreach(var t in Types(assembly.MainModule))
        {
            result[t.FullName]=new {attributes=(int)t.Attributes,interfaces=t.Interfaces.Select(i=>i.InterfaceType.FullName).ToArray(),security=Security(t),fields=t.Fields.Where(Visible).ToDictionary(f=>f.FullName,f=>new {attributes=(int)f.Attributes,marshal=Marshal(f.HasMarshalInfo?f.MarshalInfo:null)}),methods=t.Methods.Where(Visible).ToDictionary(m=>m.FullName+"|arity="+m.GenericParameters.Count,m=>new {attributes=(int)m.Attributes,implementation=(int)m.ImplAttributes,security=Security(m),parameters=m.Parameters.Select(p=>new {name=p.Name,attributes=(int)p.Attributes,marshal=Marshal(p.HasMarshalInfo?p.MarshalInfo:null)}).ToArray(),return_marshal=Marshal(m.MethodReturnType.HasMarshalInfo?m.MethodReturnType.MarshalInfo:null)})};
        }
        File.WriteAllText(output,JsonSerializer.Serialize(result,new JsonSerializerOptions{WriteIndented=true})+"\n");
    }
    static MarshalInfo? ReadMarshal(JsonElement data,ModuleDefinition module)
    {
        if(data.ValueKind==JsonValueKind.Null)return null;
        string kind=data.GetProperty("kind").GetString()!;MarshalInfo info=kind switch {
            "ArrayMarshalInfo"=>new ArrayMarshalInfo(),"CustomMarshalInfo"=>new CustomMarshalInfo(),"FixedArrayMarshalInfo"=>new FixedArrayMarshalInfo(),"FixedSysStringMarshalInfo"=>new FixedSysStringMarshalInfo(),"SafeArrayMarshalInfo"=>new SafeArrayMarshalInfo(),"MarshalInfo"=>new MarshalInfo((NativeType)data.GetProperty("values").GetProperty("NativeType").GetInt32()),_=>throw new Exception("Marshal kind "+kind)};
        foreach(var value in data.GetProperty("values").EnumerateObject())
        {
            var p=info.GetType().GetProperty(value.Name)!;if(!p.CanWrite)continue;object? result;
            if(value.Value.ValueKind==JsonValueKind.Null)result=null;
            else if(p.PropertyType.IsEnum)result=Enum.ToObject(p.PropertyType,value.Value.GetInt32());
            else if(p.PropertyType==typeof(int))result=value.Value.GetInt32();
            else if(p.PropertyType==typeof(Guid))result=Guid.Parse(value.Value.GetString()!);
            else if(p.PropertyType==typeof(string))result=value.Value.GetString();
            else if(typeof(TypeReference).IsAssignableFrom(p.PropertyType)){string name=value.Value.GetString()!;result=Types(module).SingleOrDefault(t=>t.FullName==name)??throw new Exception("Marshal managed type "+name);}
            else throw new Exception("Marshal property "+p.Name+":"+p.PropertyType);
            p.SetValue(info,result);
        }
        return info;
    }
    static void SetSecurity(ISecurityDeclarationProvider provider,JsonElement data)
    {
        provider.SecurityDeclarations.Clear();foreach(var d in data.EnumerateArray())provider.SecurityDeclarations.Add(new SecurityDeclaration((SecurityAction)d.GetProperty("action").GetInt32(),Convert.FromBase64String(d.GetProperty("blob").GetString()!)));
    }
    static void Apply(string input,string policy,string output)
    {
        using var assembly=AssemblyDefinition.ReadAssembly(input);using var document=JsonDocument.Parse(File.ReadAllText(policy));var module=assembly.MainModule;int members=0;
        foreach(var t in Types(module))
        {
            var wanted=document.RootElement.GetProperty(t.FullName);t.Attributes=(TypeAttributes)wanted.GetProperty("attributes").GetInt32();SetSecurity(t,wanted.GetProperty("security"));
            var existing=t.Interfaces.ToDictionary(i=>i.InterfaceType.FullName,i=>i.InterfaceType);t.Interfaces.Clear();
            foreach(var item in wanted.GetProperty("interfaces").EnumerateArray())
            {
                string name=item.GetString()!;TypeReference type=existing.TryGetValue(name,out var old)?old:module.GetType(name)??throw new Exception("Missing declared internal interface "+name);t.Interfaces.Add(new InterfaceImplementation(type));
            }
            foreach(var f in t.Fields.Where(Visible))
            {
                var v=wanted.GetProperty("fields").GetProperty(f.FullName);f.Attributes=(FieldAttributes)v.GetProperty("attributes").GetInt32();f.MarshalInfo=ReadMarshal(v.GetProperty("marshal"),module);members++;
            }
            foreach(var m in t.Methods.Where(Visible))
            {
                var v=wanted.GetProperty("methods").GetProperty(m.FullName+"|arity="+m.GenericParameters.Count);m.Attributes=(MethodAttributes)v.GetProperty("attributes").GetInt32();m.ImplAttributes=(MethodImplAttributes)v.GetProperty("implementation").GetInt32();SetSecurity(m,v.GetProperty("security"));
                if(m.IsInternalCall||m.IsRuntime||m.IsAbstract||m.IsPInvokeImpl)m.Body=null;
                var parameters=v.GetProperty("parameters").EnumerateArray().ToArray();if(parameters.Length!=m.Parameters.Count)throw new Exception("Parameter count "+m.FullName);
                for(int i=0;i<parameters.Length;i++){var p=m.Parameters[i];var old=parameters[i];if(p.Name!=old.GetProperty("name").GetString())throw new Exception("Parameter name "+m.FullName);p.Attributes=(ParameterAttributes)old.GetProperty("attributes").GetInt32();p.MarshalInfo=ReadMarshal(old.GetProperty("marshal"),module);}
                m.MethodReturnType.MarshalInfo=ReadMarshal(v.GetProperty("return_marshal"),module);members++;
            }
        }
        assembly.Write(output);Console.WriteLine("PASS restored declarative metadata for "+members+" source-compiled members; no publisher method body copied");
    }
    static void Main(string[] args)
    {
        if(args.Length==5)Selected=new HashSet<string>(JsonSerializer.Deserialize<string[]>(File.ReadAllText(args[4]))!);
        if(args[0]=="--record")Record(args[1],args[2]);else if(args[0]=="--apply")Apply(args[1],args[2],args[3]);else throw new Exception("mode");
    }
}
