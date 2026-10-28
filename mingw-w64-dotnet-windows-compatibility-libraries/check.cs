using System;
using System.CodeDom;
using System.CodeDom.Compiler;
using System.ComponentModel.Composition;
using System.ComponentModel.Composition.Hosting;
using System.ComponentModel.Composition.Registration;
using System.Data;
using System.Data.Odbc;
using System.Data.OleDb;
using System.DirectoryServices.AccountManagement;
using System.Globalization;
using System.IO;
using System.IO.Ports;
using System.Linq;
using System.Reflection;
using System.Reflection.Context;
using System.Security.Principal;
using System.Speech.Recognition.SrgsGrammar;
using System.Speech.Synthesis;
using System.Text.Json;
using System.Xml;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

public interface IGreeting {string Text {get;}}
[Export(typeof(IGreeting))]
public sealed class AttributedGreeting : IGreeting {public string Text=>"MEF λ";}
[Export]
public sealed class AttributedConsumer {[Import]public IGreeting Greeting {get;set;}}
public sealed class PlainGreeting : IGreeting {public string Text=>"convention λ";}
public sealed class PlainConsumer {public IGreeting Greeting {get;set;}}
internal sealed class Projection : CustomReflectionContext
{
    protected override System.Collections.Generic.IEnumerable<PropertyInfo> AddProperties(Type type)
    {
        if(type==typeof(PlainGreeting))yield return CreateProperty(MapType(typeof(string).GetTypeInfo()).AsType(),"Projected",_=>"reflection λ",null);
    }
}
internal static class Check
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static void CodeDom()
    {
        var unit=new CodeCompileUnit();var ns=new CodeNamespace("Generated");unit.Namespaces.Add(ns);
        var type=new CodeTypeDeclaration("Greeting"){IsClass=true,TypeAttributes=TypeAttributes.Public};ns.Types.Add(type);
        var method=new CodeMemberMethod{Name="Text",Attributes=MemberAttributes.Public|MemberAttributes.Static,ReturnType=new CodeTypeReference(typeof(string))};
        method.Statements.Add(new CodeMethodReturnStatement(new CodePrimitiveExpression("generated λ")));type.Members.Add(method);
        using var csharp=CodeDomProvider.CreateProvider("CSharp");using var output=new StringWriter();
        csharp.GenerateCodeFromCompileUnit(unit,output,new CodeGeneratorOptions());
        string code=output.ToString();
        var references=((string)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES")).Split(Path.PathSeparator).Select(p=>MetadataReference.CreateFromFile(p));
        var compilation=CSharpCompilation.Create("GeneratedCodeDom",new[]{CSharpSyntaxTree.ParseText(code)},references,new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
        using var binary=new MemoryStream();var result=compilation.Emit(binary);
        Require(result.Success,"generated C# compiles: "+string.Join(";",result.Diagnostics));
        var assembly=Assembly.Load(binary.ToArray());
        Require((string)assembly.GetType("Generated.Greeting").GetMethod("Text").Invoke(null,null)=="generated λ","generated code execution");
        using var vb=CodeDomProvider.CreateProvider("VisualBasic");using var vbOutput=new StringWriter();
        vb.GenerateCodeFromCompileUnit(unit,vbOutput,new CodeGeneratorOptions());
        Require(vbOutput.ToString().Contains("Class Greeting")&&vbOutput.ToString().Contains("generated λ"),"VB code generation");
        Require(csharp.IsValidIdentifier("ValidName")&&!csharp.IsValidIdentifier("1invalid"),"identifier validation");
        Console.WriteLine("PASS CodeDom C# generation/Roslyn compilation/execution, VB generation and identifier validation");
    }
    static void Composition()
    {
        using(var catalog=new TypeCatalog(typeof(AttributedGreeting),typeof(AttributedConsumer)))
        using(var container=new CompositionContainer(catalog))
        {
            var consumer=container.GetExportedValue<AttributedConsumer>();
            Require(consumer.Greeting.Text=="MEF λ"&&ReferenceEquals(consumer.Greeting,container.GetExportedValue<IGreeting>()),"attributed MEF composition/shared lifetime");
            try {container.GetExportedValue<IDisposable>();throw new Exception("missing contract accepted");}
            catch(ImportCardinalityMismatchException error){Require(error.Message.Length>0,"MEF error resources");}
        }
        var registration=new RegistrationBuilder();
        registration.ForType<PlainGreeting>().Export<IGreeting>();
        registration.ForType<PlainConsumer>().Export();
        registration.ForType<PlainConsumer>().ImportProperty(p=>p.Greeting);
        using(var catalog=new TypeCatalog(new[]{typeof(PlainGreeting),typeof(PlainConsumer)},registration))
        using(var container=new CompositionContainer(catalog))
            Require(container.GetExportedValue<PlainConsumer>().Greeting.Text=="convention λ","convention composition");
        var projected=new Projection().MapType(typeof(PlainGreeting).GetTypeInfo());
        Require((string)projected.GetProperty("Projected").GetValue(new PlainGreeting())=="reflection λ","custom reflection virtual property");
        Require(projected.Assembly.GetName().Name==typeof(Check).Assembly.GetName().Name,"projected assembly");
        Console.WriteLine("PASS attributed/convention MEF composition, imports, shared lifetime, missing exports and custom reflection projection");
    }
    static void Odbc()
    {
        var builder=new OdbcConnectionStringBuilder{Driver="msys2-nonexistent-"+Guid.NewGuid()};
        builder["Server"]="localhost";
        using var connection=new OdbcConnection(builder.ConnectionString);
        using var command=connection.CreateCommand();command.CommandText="select ?";
        command.Parameters.Add("value",OdbcType.NVarChar).Value="ODBC λ";
        Require(command.Parameters[0].OdbcType==OdbcType.NVarChar,"ODBC parameter binding");
        try {connection.Open();throw new Exception("nonexistent ODBC driver accepted");}
        catch(OdbcException error){Require(error.Errors.Count>0 && error.Errors.Cast<OdbcError>().Any(e=>e.SQLState=="IM002"||e.SQLState=="IM003"),"native ODBC diagnostics");}
        Require(connection.State==ConnectionState.Closed,"ODBC failed-open cleanup");
        Console.WriteLine("PASS native ODBC driver-manager diagnostics, parameter types, connection strings and failed-open cleanup");
    }
    static void OleDb()
    {
        var builder=new OleDbConnectionStringBuilder{Provider="SQLOLEDB"};builder["Data Source"]="fixture λ";
        Require(new OleDbConnectionStringBuilder(builder.ConnectionString).Provider=="SQLOLEDB","OLE DB connection string");
        using var command=new OleDbCommand("select ?");command.Parameters.Add("value",OleDbType.VarWChar).Value="OLE DB λ";
        Require(command.Parameters[0].OleDbType==OleDbType.VarWChar,"OLE DB parameter binding");
        using var providers=System.Data.OleDb.OleDbEnumerator.GetRootEnumerator();
        int count=0;
        while(providers.Read()){Require(providers.FieldCount>=4&&!string.IsNullOrWhiteSpace(providers.GetString(0)),"OLE DB provider metadata");count++;}
        Require(count>0,"native OLE DB providers");
        Console.WriteLine("PASS native OLE DB COM provider enumeration ("+count+" rows), metadata, parameters and connection strings");
    }
    static void Accounts()
    {
        var sid=WindowsIdentity.GetCurrent().User;
        using var context=new PrincipalContext(ContextType.Machine,Environment.MachineName);
        using var user=UserPrincipal.FindByIdentity(context,IdentityType.Sid,sid.Value);
        Require(user!=null&&user.Sid==sid&&!string.IsNullOrWhiteSpace(user.SamAccountName),"local SAM user lookup");
        using var filter=new GroupPrincipal(context);using var searcher=new PrincipalSearcher(filter);
        using var results=searcher.FindAll();int groups=0;
        foreach(var principal in results){using(principal){Require(principal.Sid!=null,"SAM group SID");groups++;}}
        Require(groups>0,"local SAM groups");
        Console.WriteLine("PASS native local SAM current-user lookup, SID/account mapping and "+groups+" read-only group results");
    }
    static void Ports()
    {
        string[] ports=SerialPort.GetPortNames();Require(ports!=null,"port enumeration");
        using var port=new SerialPort("COM65280",9600,Parity.None,8,StopBits.One);
        Require(port.BaudRate==9600&&!port.IsOpen,"serial settings");
        try {port.Open();throw new Exception("nonexistent serial port accepted");}
        catch(IOException error){Require((error.HResult&0xffff)==2||(error.HResult&0xffff)==3,"native serial port open error");}
        Require(!port.IsOpen,"serial failed-open cleanup");
        Console.WriteLine("PASS serial registry enumeration ("+ports.Length+" ports), settings and native CreateFile failure/cleanup");
    }
    static void Speech()
    {
        var rule=new SrgsRule("command",new SrgsOneOf("start","stop")){Scope=SrgsRuleScope.Public};
        var grammar=new SrgsDocument(rule){Culture=CultureInfo.GetCultureInfo("en-US")};
        using var xml=new StringWriter();using(var writer=XmlWriter.Create(xml))grammar.WriteSrgs(writer);
        using var reader=XmlReader.Create(new StringReader(xml.ToString()));var loaded=new SrgsDocument(reader);
        Require(loaded.Root.Id=="command","SRGS XML roundtrip");
        using var compiled=new MemoryStream();SrgsGrammarCompiler.Compile(loaded,compiled);
        Require(compiled.Length>32,"SRGS binary compilation");
        using var synth=new SpeechSynthesizer();
        Require(synth.GetInstalledVoices().Any(v=>v.Enabled),"native SAPI voice available");
        using var wave=new MemoryStream();synth.SetOutputToWaveStream(wave);synth.Speak("Source built speech test.");synth.SetOutputToNull();
        Require(wave.Length>44&&System.Text.Encoding.ASCII.GetString(wave.ToArray(),0,4)=="RIFF","SAPI WAV output");
        Console.WriteLine("PASS SRGS XML/binary grammar compilation and native SAPI speech synthesis to WAV ("+wave.Length+" bytes)");
    }
    static void Main(string[] args)
    {
        CodeDom();Composition();Odbc();OleDb();Accounts();Ports();Speech();
        CheckResources.Run(args[0],args[1]);
    }
}
