using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using Mono.Cecil;
using Mono.Cecil.Cil;
using Mono.Cecil.Rocks;

static class Program
{
    static void Require(bool value,string message) { if(!value)throw new Exception(message); }
    static void Identity(Assembly assembly)
    {
        Require(assembly.GetName().Version==new Version(0,11,0,0),"Original version: "+assembly.FullName);
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="50cebf1cceb9d05e","Original signing identity");
        Require(assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName==".NETStandard,Version=v2.0","Original NS2 target");
    }
    static void CopyNullable(Mono.Cecil.ICustomAttributeProvider source,Mono.Cecil.ICustomAttributeProvider target)
    {
        foreach(var attribute in target.CustomAttributes.Where(a=>a.AttributeType.FullName.StartsWith("System.Runtime.CompilerServices.Nullable")).ToArray())
            target.CustomAttributes.Remove(attribute);
        foreach(var attribute in source.CustomAttributes.Where(a=>a.AttributeType.FullName.StartsWith("System.Runtime.CompilerServices.Nullable")))
        {
            var copy=new CustomAttribute(attribute.Constructor);
            foreach(var argument in attribute.ConstructorArguments)copy.ConstructorArguments.Add(argument);
            target.CustomAttributes.Add(copy);
        }
    }
    static int Invoke(string path,string context)
    {
        var load=new AssemblyLoadContext(context,true);
        var assembly=load.LoadFromAssemblyPath(path);
        int value=(int)assembly.GetType("Owned.Box")!.GetMethod("Value")!.Invoke(null,null)!;
        load.Unload();return value;
    }
    static void Main(string[] args)
    {
        if(args[0]=="--dump-api") { Api.Dump(args[1],args[2]);return; }
        foreach(var name in new[]{"Mono.Cecil","Mono.Cecil.Rocks","Mono.Cecil.Mdb","Mono.Cecil.Pdb"})Identity(Assembly.Load(name));
        Require(new Mono.Cecil.Mdb.MdbReaderProvider()!=null && new Mono.Cecil.Pdb.NativePdbReaderProvider()!=null,"Original symbol providers");
        string fixture=Path.GetFullPath(args[0]),output=Path.GetFullPath(args[1]);Directory.CreateDirectory(output);
        using var resolver=new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(Path.GetDirectoryName(typeof(object).Assembly.Location)!);
        resolver.AddSearchDirectory(Path.GetDirectoryName(fixture)!);
        var read=new ReaderParameters{ReadSymbols=true,ReadingMode=ReadingMode.Immediate,AssemblyResolver=resolver};
        using(var assembly=AssemblyDefinition.ReadAssembly(fixture,read))
        {
            var type=assembly.MainModule.GetType("Owned.Box");
            var method=type.Methods.Single(m=>m.Name=="Value");
            Require(method.DebugInformation.SequencePoints.Count>0,"Original portable PDB sequence points");
            method.Body.SimplifyMacros();
            Require(method.Body.Instructions[0].OpCode==OpCodes.Ldc_I4 && (int)method.Body.Instructions[0].Operand==1,"Original IL negative control");
            method.Body.Instructions[0].Operand=42;
            method.Body.OptimizeMacros();
            var annotated=type.Methods.Single(m=>m.Name=="Annotated");
            var unannotated=type.Methods.Single(m=>m.Name=="Unannotated");
            int count=annotated.CustomAttributes.Count(a=>a.AttributeType.Name.StartsWith("Nullable"))+
                annotated.MethodReturnType.CustomAttributes.Count(a=>a.AttributeType.Name.StartsWith("Nullable"))+
                annotated.Parameters[0].CustomAttributes.Count(a=>a.AttributeType.Name.StartsWith("Nullable"));
            Require(count>0,"Owned nullable annotation fixture");
            CopyNullable(annotated,unannotated);CopyNullable(annotated.MethodReturnType,unannotated.MethodReturnType);
            CopyNullable(annotated.Parameters[0],unannotated.Parameters[0]);
            assembly.MainModule.Resources.Add(new EmbeddedResource("owned.annotation.marker",Mono.Cecil.ManifestResourceAttributes.Private,new byte[]{1,2,3,4}));
            assembly.Write(Path.Combine(output,"OwnedFixture.dll"),new WriterParameters{WriteSymbols=true,SymbolWriterProvider=new PortablePdbWriterProvider()});
        }
        string rewritten=Path.Combine(output,"OwnedFixture.dll");
        Require(Invoke(fixture,"original")==1 && Invoke(rewritten,"rewritten")==42,"Actual original/rewritten IL execution");
        using(var reopened=AssemblyDefinition.ReadAssembly(rewritten,new ReaderParameters{ReadSymbols=true,AssemblyResolver=resolver}))
        {
            Require(reopened.MainModule.GetType("Owned.Box").Methods.Single(m=>m.Name=="Value").DebugInformation.SequencePoints.Count>0,"Written portable PDB sequence points");
            Require(((EmbeddedResource)reopened.MainModule.Resources.Single(r=>r.Name=="owned.annotation.marker")).GetResourceData().SequenceEqual(new byte[]{1,2,3,4}),"Written embedded resource");
            // Also exercise the original embedded-portable-PDB writer/reader path.
            reopened.Write(Path.Combine(output,"embedded.dll"),new WriterParameters{WriteSymbols=true,SymbolWriterProvider=new EmbeddedPortablePdbWriterProvider()});
        }
        using(var embedded=AssemblyDefinition.ReadAssembly(Path.Combine(output,"embedded.dll"),new ReaderParameters{ReadSymbols=true,AssemblyResolver=resolver}))
            Require(embedded.MainModule.HasSymbols,"Embedded portable PDB round trip");
        var beforeContext=new AssemblyLoadContext("nullable-before",true);
        var afterContext=new AssemblyLoadContext("nullable-after",true);
        var before=beforeContext.LoadFromAssemblyPath(fixture).GetType("Owned.Box")!.GetMethod("Unannotated")!;
        var after=afterContext.LoadFromAssemblyPath(rewritten).GetType("Owned.Box")!.GetMethod("Unannotated")!;
        var nullability=new NullabilityInfoContext();
        Require(nullability.Create(before.ReturnParameter).ReadState==NullabilityState.NotNull,"Nullable metadata negative control");
        Require(nullability.Create(after.ReturnParameter).ReadState==NullabilityState.Nullable && nullability.Create(after.GetParameters()[0]).ReadState==NullabilityState.Nullable,"Transferred nullable method/parameter metadata: "+nullability.Create(after.ReturnParameter).ReadState+"/"+nullability.Create(after.GetParameters()[0]).ReadState);
        beforeContext.Unload();afterContext.Unload();
        Api.Check(args[2]);
        Console.WriteLine("PASS all four original NS2 identities and original MDB/native-PDB provider types");
        Console.WriteLine("PASS IL rewrite with Rocks macro transforms executes 1 -> 42; portable/embedded PDB and resource round trips");
        Console.WriteLine("PASS actual nullable metadata transfer changes reflection return/parameter contracts from NotNull to Nullable");
    }
}
