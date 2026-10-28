using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;

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
        Name(p.ParameterType)+(p.IsOut?" out":"")+(p.IsIn&&p.ParameterType.IsByRef?" in":"")+(p.IsOptional?" optional":"")));
    static SortedSet<string> Surface(Assembly assembly, bool inherited=false)
    {
        var result=new SortedSet<string>();
        foreach(var type in assembly.GetExportedTypes().Concat(assembly.GetForwardedTypes()).Distinct())
        {
            string prefix=Name(type)+" ";
            result.Add(prefix+"type "+(type.IsInterface?"interface":type.IsEnum?"enum":type.IsValueType?"struct":"class")+" base="+Name(type.BaseType));
            // Introducing an intermediate base retains assignability to the
            // contract's base. This gate checks that relationship, not layout.
            if(inherited && !type.IsInterface && !type.IsValueType)
                for(var ancestor=type.BaseType?.BaseType;ancestor!=null;ancestor=ancestor.BaseType)
                    result.Add(prefix+"type class base="+Name(ancestor));
            foreach(var iface in type.GetInterfaces()) result.Add(prefix+"interface "+Name(iface));
            foreach(var c in type.GetConstructors(Members).Where(Visible)) result.Add(prefix+"ctor("+Params(c)+")");
            foreach(var m in type.GetMethods(inherited ? Members & ~BindingFlags.DeclaredOnly : Members).Where(Visible))
                result.Add(prefix+"method "+(m.IsStatic?"static ":"")+Name(m.ReturnType)+" "+m.Name+"`"+m.GetGenericArguments().Length+"("+Params(m)+")");
            foreach(var f in type.GetFields(inherited ? Members & ~BindingFlags.DeclaredOnly : Members).Where(f=>f.IsPublic||f.IsFamily||f.IsFamilyOrAssembly))
                result.Add(prefix+"field "+(f.IsStatic?"static ":"")+Name(f.FieldType)+" "+f.Name+(f.IsLiteral?"="+f.GetRawConstantValue():""));
        }
        // Direct forwarding to the implementation and forwarding through a
        // second facade resolve to the same type; check the forwarded surface.
        foreach(var type in assembly.GetForwardedTypes()) result.Add("forward "+Name(type));
        return result;
    }
    sealed class SourceContext : AssemblyLoadContext
    {
        readonly string dependencies;
        internal SourceContext(string name,string directory):base(name,true){dependencies=directory;}
        protected override Assembly Load(AssemblyName name)
        {
            string[] files=System.IO.Directory.GetFiles(dependencies,name.Name+".dll",System.IO.SearchOption.AllDirectories);
            return files.Length==1?LoadFromAssemblyPath(files[0]):null;
        }
    }
    static int Main(string[] args)
    {
        var expectedContext=new SourceContext("upstream-contract",System.IO.Path.GetDirectoryName(System.IO.Path.GetFullPath(args[0])));
        var actualContext=new SourceContext("implementation",args[2]);
        Assembly expected=expectedContext.LoadFromAssemblyPath(System.IO.Path.GetFullPath(args[0]));
        Assembly actual=actualContext.LoadFromAssemblyPath(System.IO.Directory.GetFiles(args[1],expected.GetName().Name+".dll",System.IO.SearchOption.AllDirectories).Single());
        var wanted=Surface(expected); var got=Surface(actual,true);
        string[] missing=wanted.Except(got).ToArray();
        using var audit=JsonDocument.Parse(System.IO.File.ReadAllText(args[3]));
        string[] upstream=audit.RootElement.GetProperty("members").EnumerateArray()
            .Where(e=>e.GetProperty("assembly").GetString()==expected.GetName().Name)
            .Select(e=>e.GetProperty("signature").GetString()).ToArray();
        string[] unexpected=missing.Except(upstream).ToArray();
        foreach(string entry in unexpected) Console.Error.WriteLine("MISSING API: "+entry);
        foreach(string entry in missing.Intersect(upstream)) Console.WriteLine("VERIFIED UPSTREAM MISMATCH: "+entry);
        string[] changed=upstream.Except(missing).ToArray();
        foreach(string entry in changed) Console.Error.WriteLine("UPSTREAM AUDIT CHANGED; REVIEW REQUIRED: "+entry);
        if(unexpected.Length!=0||changed.Length!=0) return 1;
        Console.WriteLine("PASS: "+actual.GetName().Name+" checks "+(wanted.Count-missing.Length)+
            " upstream public/protected type/member signatures; "+missing.Length+" published upstream mismatches retained");
        return 0;
    }
}
