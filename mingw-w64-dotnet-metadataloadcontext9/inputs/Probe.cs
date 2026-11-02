using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Versioning;
using System.Text.Json;
internal static class Probe
{
    static void Require(bool condition,string message) { if(!condition)throw new Exception(message); }
    sealed class TrackingResolver:MetadataAssemblyResolver
    {
        readonly PathAssemblyResolver inner;
        internal int Calls;
        internal TrackingResolver(IEnumerable<string> paths) { inner=new PathAssemblyResolver(paths); }
        public override Assembly? Resolve(MetadataLoadContext context,AssemblyName name) { Calls++;return inner.Resolve(context,name); }
    }
    static int Main(string[] args)
    {
        string output=args[0],refs=args[1],sentinel=Path.Combine(output,"execution-sentinel.txt");
        Environment.SetEnvironmentVariable("MLC9_SENTINEL",sentinel);
        var implementation=typeof(MetadataLoadContext).Assembly;
        Require(implementation.GetName().Version==new Version(9,0,0,11),"Original servicing OOB assembly version");
        Require(Convert.ToHexString(implementation.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="cc7b13ffcd2ddd51","Original Open signing key");
        Require(implementation.GetCustomAttribute<TargetFrameworkAttribute>()?.FrameworkName==".NETCoreApp,Version=v9.0","Original NET9 target");
        Require(implementation.GetCustomAttribute<CLSCompliantAttribute>()?.IsCompliant==true,"Original CLS policy");
        Require(Path.GetDirectoryName(implementation.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"Consumer-local source implementation");
        var expected=JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(Path.Combine(output,"neutral-strings.json")))!;
        Require(expected.Count>0,"Original resource baseline");
        var resources=new ResourceManager("FxResources.System.Reflection.MetadataLoadContext.SR",implementation);
        using var set=resources.GetResourceSet(CultureInfo.InvariantCulture,true,false)!;Require(set.Cast<System.Collections.DictionaryEntry>().Count()==expected.Count,"Original resource count");
        foreach(var pair in expected)Require(resources.GetString(pair.Key,CultureInfo.InvariantCulture)==pair.Value,"Original resource value:"+pair.Key);
        string any=Path.Combine(output,"FixtureAny.dll"),x86=Path.Combine(output,"FixtureX86.dll");
        var paths=Directory.GetFiles(refs,"*.dll").Concat(new[]{any,x86}).ToArray();
        var resolver=new TrackingResolver(paths);
        using(var context=new MetadataLoadContext(resolver,"System.Runtime"))
        {
            var assembly=context.LoadFromAssemblyPath(any);
            Require(assembly.ReflectionOnly,"Metadata-only assembly");
            Require(ReferenceEquals(assembly,context.LoadFromAssemblyName("FixtureAny")),"Assembly-name/path cache identity");
            var type=assembly.GetType("Fixtures.Sample",true)!;
            Require((string)type.GetField("Text")!.GetRawConstantValue()! == "λ世界","Unicode metadata constant");
            Require(type.GetMethod("Optional")!.GetParameters()[0].IsOptional&&(int)type.GetMethod("Optional")!.GetParameters()[0].RawDefaultValue! == 7,"Optional/default parameter metadata");
            bool defaultValueRejected=false;try{_ = type.GetMethod("Optional")!.GetParameters()[0].DefaultValue;}catch(InvalidOperationException){defaultValueRejected=true;}Require(defaultValueRejected,"Metadata DefaultValue directs callers to RawDefaultValue");
            Require(type.GetMethod("Echo")!.IsGenericMethodDefinition,"Generic method metadata");
            Require(type.GetMethod("ReturnRef")!.ReturnType.IsByRef,"Byref return metadata");
            Require(type.GetInterfaces().Any(t=>t.FullName=="System.IDisposable"),"Interface metadata");
            var attribute=type.GetCustomAttributesData().Single(a=>a.AttributeType.FullName=="Fixtures.TagAttribute");
            Require((string)attribute.ConstructorArguments[0].Value! == "λ世界","Custom attribute decoded without running constructor");
            bool invocationRejected=false;try{type.GetMethod("Answer")!.Invoke(null,null);}catch(InvalidOperationException){invocationRejected=true;}Require(invocationRejected,"Metadata method execution rejected");
            bool attributesRejected=false;try{type.GetCustomAttributes(false);}catch(InvalidOperationException){attributesRejected=true;}Require(attributesRejected,"Attribute instantiation rejected");
            var generic=assembly.GetType("Fixtures.GenericBox`1",true)!;var flags=generic.GetGenericArguments()[0].GenericParameterAttributes;
            Require((flags&(GenericParameterAttributes.ReferenceTypeConstraint|GenericParameterAttributes.DefaultConstructorConstraint))==(GenericParameterAttributes.ReferenceTypeConstraint|GenericParameterAttributes.DefaultConstructorConstraint),"Generic constraints");
            var plain=assembly.GetType("Fixtures.Plain",true)!;Require(generic.MakeGenericType(plain).GetProperty("Item")!.PropertyType==plain,"Closed generic property substitution");
            var cross=context.LoadFromByteArray(File.ReadAllBytes(x86));Require(cross.GetName().Name=="FixtureX86"&&cross.GetType("Fixtures.Sample",true)!=null,"Cross-architecture PE metadata");
            Require(context.GetAssemblies().Count()>=3&&resolver.Calls>0,"Context enumeration and custom resolver calls");
            using var stream=File.OpenRead(any);Require(context.LoadFromStream(stream)==assembly,"Stream load shares assembly identity");
        }
        using(var first=new MetadataLoadContext(new PathAssemblyResolver(paths),"System.Runtime"))
        using(var second=new MetadataLoadContext(new PathAssemblyResolver(paths),"System.Runtime"))
            Require(first.LoadFromAssemblyPath(any).GetType("Fixtures.Sample")!=second.LoadFromAssemblyPath(any).GetType("Fixtures.Sample"),"Independent context type identities");
        using(var invalid=new MetadataLoadContext(new PathAssemblyResolver(paths),"System.Runtime"))
        {
            bool bad=false;try{invalid.LoadFromByteArray(new byte[]{1,2,3,4});}catch(BadImageFormatException){bad=true;}Require(bad,"Invalid PE rejected");
            bool missing=false;try{invalid.LoadFromAssemblyName("Missing.OriginalFixture");}catch(FileNotFoundException){missing=true;}Require(missing,"Unresolved assembly rejected");
        }
        var disposed=new MetadataLoadContext(new PathAssemblyResolver(paths),"System.Runtime");var pending=disposed.LoadFromAssemblyPath(any);disposed.Dispose();bool disposedRejected=false;
        try{pending.GetTypes();}catch(ObjectDisposedException){disposedRejected=true;}Require(disposedRejected,"Metadata access after context disposal rejected");
        Require(!File.Exists(sentinel),"No module initializer or attribute constructor executed");
        Require(!AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetName().Name is "FixtureAny" or "FixtureX86"),"Metadata fixtures never entered runtime load context");
        Console.WriteLine("PASS source NET9 MetadataLoadContext:servicing identity,all"+expected.Count+" resources,Unicode/generics/attributes/byref/defaults,resolver/cache,path/stream/bytes,x86 PE,isolation,invalid inputs,disposal and no fixture execution");
        return 0;
    }
}
