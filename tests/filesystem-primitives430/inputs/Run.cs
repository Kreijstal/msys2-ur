using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;

sealed class Context : AssemblyLoadContext
{
    internal Context() : base(isCollectible: true) { }
    protected override Assembly? Load(AssemblyName name) => Default.LoadFromAssemblyName(name);
}
static class Program
{
    static void Require(bool value,string message) { if (!value) throw new Exception(message); }
    static void Main(string[] args)
    {
        using var policy=JsonDocument.Parse(File.ReadAllText(args[1]));
        foreach (string label in new[]{"lib-netstandard1.3","ref-net46"})
        {
            var context=new Context(); string[] parts=label.Split('-');
            var assembly=context.LoadFromAssemblyPath(Path.GetFullPath(Path.Combine(args[0],parts[0],parts[1],"System.IO.FileSystem.Primitives.dll")));
            foreach(string name in new[]{"FileAccess","FileAttributes","FileMode","FileShare"})
            {
                Type type=assembly.GetType("System.IO."+name,true)!;
                if(label=="lib-netstandard1.3") Require(type.Assembly==assembly && !assembly.CustomAttributes.Any(a=>a.AttributeType.FullName=="System.Runtime.CompilerServices.ReferenceAssemblyAttribute"),"Actual candidate enum implementation must execute");
                else Require(type.Assembly!=assembly && type.Assembly.Location.Replace('\\','/').Contains("/shared/Microsoft.NETCore.App/8.0.31/"),"Facade must forward to source NET8 implementation");
                var actualNames=type.GetFields(BindingFlags.Public|BindingFlags.Static).Select(f=>f.Name).OrderBy(n=>n).ToArray();
                var expectedNames=policy.RootElement.GetProperty("System.IO.FileSystem.Primitives.dll").GetProperty("api").EnumerateArray().Select(v=>v.GetString()!).Where(v=>v.StartsWith("F System.IO."+name+" System.IO."+name+"::")).Select(v=>v.Split("::")[1].Split('|')[0]).OrderBy(n=>n).ToArray();
                Require(label=="lib-netstandard1.3" ? actualNames.SequenceEqual(expectedNames) : expectedNames.All(n=>actualNames.Contains(n)),"Original enum names; exact candidate or source-host facade target superset");
                foreach(var field in type.GetFields(BindingFlags.Public|BindingFlags.Static).Where(f=>expectedNames.Contains(f.Name)))
                {
                    string key="F System.IO."+name+" System.IO."+name+"::"+field.Name+"|";
                    var api=policy.RootElement.GetProperty("System.IO.FileSystem.Primitives.dll").GetProperty("api").EnumerateArray().Select(v=>v.GetString()!).Single(v=>v.StartsWith(key));
                    int wanted=int.Parse(api.Split("constant=")[1]); Require(Convert.ToInt32(field.GetRawConstantValue())==wanted,"Original enum constant "+field.Name);
                }
                object parsed=Enum.Parse(type,name=="FileMode"?"OpenOrCreate":name=="FileAccess"?"ReadWrite":name=="FileShare"?"Read, Delete":"ReadOnly, Hidden");
                Require(Convert.ToInt32(parsed)==(name=="FileMode"?4:name=="FileShare"?5:3),"Candidate enum parsing and flags");
                Require(Enum.GetUnderlyingType(type)==typeof(int),"Original enum underlying type");
            }
            Console.WriteLine("PASS "+label+": all original enum constants, underlying types and parsing/flag behavior"); context.Unload();
        }
    }
}
