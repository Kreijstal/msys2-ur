using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;

// Compare public/protected type/member signatures against the checked-in upstream
// net8.0 contract. This is an API-surface gate; native behavior is checked separately.
internal static class Program
{
    const BindingFlags Members=BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static|BindingFlags.DeclaredOnly;
    static string Name(Type type)
    {
        if(type==null) return "-";
        if(type.IsGenericParameter) return (type.DeclaringMethod==null?"!":"!!")+type.GenericParameterPosition;
        if(type.IsByRef) return Name(type.GetElementType())+"&";
        if(type.IsPointer) return Name(type.GetElementType())+"*";
        if(type.IsArray) return Name(type.GetElementType())+"["+new string(',',type.GetArrayRank()-1)+"]";
        return type.IsGenericType ? type.GetGenericTypeDefinition().FullName+"<"+string.Join(",",type.GetGenericArguments().Select(Name))+">" : type.FullName;
    }
    static bool Visible(MethodBase m)=>m.IsPublic||m.IsFamily||m.IsFamilyOrAssembly;
    static string Params(MethodBase method)=>string.Join(",",method.GetParameters().Select(p=>
        Name(p.ParameterType)+(p.IsOut?" out":"")+(p.IsIn?" in":"")+(p.IsOptional?" optional":"")));
    static SortedSet<string> Surface(Assembly assembly, bool inherited=false)
    {
        var result=new SortedSet<string>();
        foreach(var type in assembly.GetExportedTypes())
        {
            string prefix=Name(type)+" ";
            result.Add(prefix+"type "+(type.IsInterface?"interface":type.IsEnum?"enum":type.IsValueType?"struct":"class")+" base="+Name(type.BaseType));
            foreach(var iface in type.GetInterfaces()) result.Add(prefix+"interface "+Name(iface));
            foreach(var c in type.GetConstructors(Members).Where(Visible)) result.Add(prefix+"ctor("+Params(c)+")");
            foreach(var m in type.GetMethods(inherited ? Members & ~BindingFlags.DeclaredOnly : Members).Where(Visible))
                result.Add(prefix+"method "+(m.IsStatic?"static ":"")+Name(m.ReturnType)+" "+m.Name+"`"+m.GetGenericArguments().Length+"("+Params(m)+")");
            foreach(var f in type.GetFields(inherited ? Members & ~BindingFlags.DeclaredOnly : Members).Where(f=>f.IsPublic||f.IsFamily||f.IsFamilyOrAssembly))
                result.Add(prefix+"field "+(f.IsStatic?"static ":"")+Name(f.FieldType)+" "+f.Name+(f.IsLiteral?"="+f.GetRawConstantValue():""));
        }
        return result;
    }
    static int Main(string[] args)
    {
        var expectedContext=new AssemblyLoadContext("upstream-contract",true);
        var actualContext=new AssemblyLoadContext("implementation",true);
        Assembly expected=expectedContext.LoadFromAssemblyPath(System.IO.Path.GetFullPath(args[0]));
        Assembly actual=actualContext.LoadFromAssemblyPath(System.IO.Path.GetFullPath(args[1]));
        var wanted=Surface(expected); var got=Surface(actual,true);
        string[] missing=wanted.Except(got).ToArray();
        foreach(string entry in missing) Console.Error.WriteLine("MISSING API: "+entry);
        if(missing.Length!=0) return 1;
        Console.WriteLine("PASS: "+actual.GetName().Name+" implements all "+wanted.Count+" upstream public/protected type/member signatures");
        return 0;
    }
}
