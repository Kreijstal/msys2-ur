using System;
using System.CodeDom;
using System.CodeDom.Compiler;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Versioning;
using System.Text;
using System.Text.Json;
using System.Collections.Generic;
using Microsoft.CSharp;
using Microsoft.VisualBasic;
internal static class Probe
{
    static void Require(bool condition,string message) { if(!condition)throw new Exception(message); }
    static int Main(string[] args)
    {
        var assembly=typeof(CodeDomProvider).Assembly;
        Require(assembly.GetCustomAttribute<CLSCompliantAttribute>()?.IsCompliant==true,"Original upstream CLSCompliant property");
        Require(assembly.GetName().Version==new Version(9,0,0,0),"NET9 assembly identity");
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="cc7b13ffcd2ddd51","Original Open signing key");
        Require(assembly.GetCustomAttribute<TargetFrameworkAttribute>()?.FrameworkName==".NETCoreApp,Version=v9.0","Original NET9 target");
        Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"Consumer-local source CodeDom");
        var manager=new ResourceManager("FxResources.System.CodeDom.SR",assembly);
        using var set=manager.GetResourceSet(System.Globalization.CultureInfo.InvariantCulture,true,false)!;
        Require(set.Cast<System.Collections.DictionaryEntry>().Count()==22,"All22 original neutral resource strings");
        Require(new CodeTypeReference((string)null!).BaseType=="System.Void","Original shared-source nullable string constructor");
        Require(new CodeTypeReference((string)null!,CodeTypeReferenceOptions.GlobalReference).BaseType=="System.Void","Original shared-source nullable string/options constructor");
        Require(new CodeTypeReference(typeof(int)).ArrayElementType==null,"Original shared-source nullable scalar ArrayElementType");
        var expectedStrings=JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(Path.Combine(args[0],"neutral-strings.json")))!;
        Require(expectedStrings.Count==22,"Original resource value baseline");
        foreach(var entry in expectedStrings)Require(manager.GetString(entry.Key,System.Globalization.CultureInfo.InvariantCulture)==entry.Value,"Original resource value: "+entry.Key);
        var unit=new CodeCompileUnit();var ns=new CodeNamespace("Παράδειγμα");unit.Namespaces.Add(ns);
        var type=new CodeTypeDeclaration("世界"){IsClass=true,TypeAttributes=TypeAttributes.Public};ns.Types.Add(type);
        var method=new CodeMemberMethod{Name="Answer",Attributes=MemberAttributes.Public|MemberAttributes.Static,ReturnType=new CodeTypeReference(typeof(int))};
        method.Statements.Add(new CodeMethodReturnStatement(new CodeBinaryOperatorExpression(new CodePrimitiveExpression(40),CodeBinaryOperatorType.Add,new CodePrimitiveExpression(2))));type.Members.Add(method);
        foreach(var pair in new (CodeDomProvider provider,string suffix)[]{(new CSharpCodeProvider(),"cs"),(new VBCodeProvider(),"vb")})
        {
            using var provider=pair.provider;using var writer=new StringWriter();provider.GenerateCodeFromCompileUnit(unit,writer,new CodeGeneratorOptions());
            string code=writer.ToString();Require(code.Contains("世界")&&code.Contains("Answer"),"Unicode source generation");
            File.WriteAllText(Path.Combine(args[0],"Generated."+pair.suffix),code,new UTF8Encoding(false));
            Require(provider.IsValidIdentifier("Answer"),"Valid identifier");
            Require(provider.CreateEscapedIdentifier(pair.suffix=="cs"?"class":"Class")!=(pair.suffix=="cs"?"class":"Class"),"Keyword escaping");
            bool rejected=false;try{provider.CompileAssemblyFromSource(new CompilerParameters(),code);}catch(PlatformNotSupportedException){rejected=true;}
            Require(rejected,"Original NET9 external-compiler API reports PlatformNotSupported");
        }
        if(args.Length>1)
            foreach(string name in new[]{"GeneratedCs.dll","GeneratedVb.dll"})
            {
                var generated=Assembly.LoadFile(Path.GetFullPath(Path.Combine(args[0],name)));
                Require((int)generated.GetType("Παράδειγμα.世界",true)!.GetMethod("Answer")!.Invoke(null,null)! == 42,"Source compiler output executes: "+name);
            }
        Console.WriteLine("PASS original NET9 CodeDom identity/resources,CSharp/VB Unicode generation,identifiers and documented unsupported compiler API"+(args.Length>1?";both generated libraries execute to42":""));
        return 0;
    }
}
