using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Resources;
using System.Runtime.Loader;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Emit;
using Microsoft.CodeAnalysis.Text;
using Microsoft.CodeAnalysis.VisualBasic;
using Microsoft.CodeAnalysis.VisualBasic.Syntax;

class Program
{
 static void Require(bool ok,string message){if(!ok)throw new Exception(message);}
 sealed class ProbeAnalyzer:DiagnosticAnalyzer
 {
  public int Calls;
  static readonly DiagnosticDescriptor Rule=new("OWNVB001","VB callback","VB literal callback","Owned",DiagnosticSeverity.Warning,true);
  public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics=>ImmutableArray.Create(Rule);
  public override void Initialize(AnalysisContext context)
  {
   context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);context.EnableConcurrentExecution();
   context.RegisterSyntaxNodeAction(c=>{Interlocked.Increment(ref Calls);if(c.Node.GetFirstToken().ValueText=="42")c.ReportDiagnostic(Diagnostic.Create(Rule,c.Node.GetLocation()));},SyntaxKind.NumericLiteralExpression);
  }
 }
 sealed class ProbeGenerator:ISourceGenerator
 {
  public void Initialize(GeneratorInitializationContext context){}
  public void Execute(GeneratorExecutionContext context)=>context.AddSource("GeneratedOwned.vb",SourceText.From("Public Module GeneratedOwned\nPublic Function Value() As Integer\nReturn 73\nEnd Function\nEnd Module\n",Encoding.UTF8));
 }
 static async Task Main(string[] args)
 {
  var assembly=typeof(VisualBasicCompilation).Assembly;
  Require(assembly.GetName().Version==new Version(4,9,0,0),"Assembly version");
  Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="31bf3856ad364e35","Assembly identity");
  Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="4.9.2+9934fb9e3527e1c0c51314e57d4aab30f97e8f9e","Source informational version");
  Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"Consumer-local source library");
  using var localizations=JsonDocument.Parse(File.ReadAllText(args[0]));int sets=0,strings=0;
  foreach(var entry in localizations.RootElement.EnumerateArray())
  {
   string culture=entry.GetProperty("culture").GetString();Assembly target=assembly;
   if(culture.Length>0)target=assembly.GetSatelliteAssembly(CultureInfo.GetCultureInfo(culture));
   string name=entry.GetProperty("resource").GetString()+(culture.Length>0?"."+culture:"")+".resources";
   using var reader=new ResourceReader(target.GetManifestResourceStream(name)??throw new Exception(name));
   var actual=reader.Cast<DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value);
   Require(actual.Count==entry.GetProperty("strings").EnumerateObject().Count(),"Resource count");
   foreach(var value in entry.GetProperty("strings").EnumerateObject()){Require(actual.TryGetValue(value.Name,out string text)&&text==value.Value.GetString(),"Source resource "+culture+"/"+value.Name);strings++;}sets++;
  }
  Require(sets==14&&strings==25130,"Complete neutral + 13 cultures");
  Console.WriteLine($"PASS source compiler identity, {sets} resource sets/{strings} strings and thirteen satellite assemblies");
  var references=Directory.GetFiles(args[1],"*.dll").Select(p=>MetadataReference.CreateFromFile(p)).ToArray();
  var options=new VisualBasicCompilationOptions(OutputKind.DynamicallyLinkedLibrary,optionStrict:OptionStrict.On).WithGlobalImports(GlobalImport.Parse("System"),GlobalImport.Parse("System.Collections.Generic"),GlobalImport.Parse("System.Linq"));
  VisualBasicCompilation Compile(string code,string name,VisualBasicCompilationOptions custom=null,IEnumerable<MetadataReference> refs=null)=>VisualBasicCompilation.Create(name,new[]{VisualBasicSyntaxTree.ParseText(SourceText.From(code,Encoding.UTF8),new VisualBasicParseOptions(LanguageVersion.Latest),path:"Owned π.vb")},refs??references,custom??options);
  const string code="""
Imports System.Threading.Tasks
Imports System.Xml.Linq
Public Module Owned
    Public Function Run() As Integer
        Dim values = {1, 2, 3}
        Dim q = From v In values Where v > 1 Select v * 10
        Dim e = <root><%= q.Select(Function(x) <v><%= x %></v>) %></root>
        Dim box = New Box(Of Integer)(42)
        Dim anonymous = New With {.Value = box.Value}
        Return anonymous.Value + e.Elements("v").Count() + IteratorValues().Sum()
    End Function
    Private Iterator Function IteratorValues() As IEnumerable(Of Integer)
        Yield 1
        Yield 2
    End Function
    Public Async Function RunAsync() As Task(Of Integer)
        Await Task.Yield()
        Return Run()
    End Function
End Module
Public Class Box(Of T)
    Public ReadOnly Property Value As T
    Public Sub New(value As T)
        Me.Value = value
    End Sub
End Class
""";
  var compilation=Compile(code,"OwnedVB");
  Require(!compilation.GetDiagnostics().Any(d=>d.Severity==DiagnosticSeverity.Error),"VB binding: "+string.Join(";",compilation.GetDiagnostics()));
  var tree=compilation.SyntaxTrees.Single();var model=compilation.GetSemanticModel(tree);
  var method=tree.GetRoot().DescendantNodes().OfType<MethodStatementSyntax>().Single(m=>m.Identifier.ValueText=="Run");
  Require(model.GetDeclaredSymbol(method).ReturnType.SpecialType==SpecialType.System_Int32,"Method semantic return type");
  var analyzer=new ProbeAnalyzer();var diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create<DiagnosticAnalyzer>(analyzer)).GetAnalyzerDiagnosticsAsync();
  Require(analyzer.Calls>0&&diagnostics.Count(d=>d.Id=="OWNVB001")==1&&!diagnostics.Any(d=>d.Id=="AD0001"),"Real VB analyzer callbacks");
  using var pe=new MemoryStream();using var pdb=new MemoryStream();
  var emitted=compilation.Emit(pe,pdb,options:new EmitOptions(debugInformationFormat:DebugInformationFormat.PortablePdb));
  Require(emitted.Success,"VB emit: "+string.Join(";",emitted.Diagnostics));
  pe.Position=0;pdb.Position=0;
  using(var provider=MetadataReaderProvider.FromPortablePdbStream(pdb,MetadataStreamOptions.LeaveOpen))Require(provider.GetMetadataReader().Documents.Count>0,"Portable PDB documents");
  pdb.Position=0;var load=new AssemblyLoadContext("OwnedVB",isCollectible:true);var emittedAssembly=load.LoadFromStream(pe,pdb);
  Require((int)emittedAssembly.GetType("Owned").GetMethod("Run").Invoke(null,null)==47,"Executed generics/LINQ/XML/anonymous/iterator IL");
  Require(await (Task<int>)emittedAssembly.GetType("Owned").GetMethod("RunAsync").Invoke(null,null)==47,"Executed async/await IL");
  load.Unload();Console.WriteLine("PASS VB syntax/semantics, generics, query/XML literals, anonymous types, iterator, async/await, analyzer callbacks, portable PDB and executed IL");
  const string checkedCode="Public Module OverflowOwned\nPublic Function Add(x As Integer) As Integer\nReturn x + 1\nEnd Function\nEnd Module\n";
  foreach(bool check in new[]{false,true})
  {
   var c=Compile(checkedCode,"OverflowOwned"+check,options.WithOverflowChecks(check));using var bytes=new MemoryStream();var result=c.Emit(bytes);Require(result.Success,"Overflow fixture emit");bytes.Position=0;
   var context=new AssemblyLoadContext("Overflow"+check,true);var a=context.LoadFromStream(bytes);bool threw=false;
   try{int value=(int)a.GetType("OverflowOwned").GetMethod("Add").Invoke(null,new object[]{int.MaxValue});Require(!check&&value==int.MinValue,"Unchecked overflow result");}
   catch(TargetInvocationException e)when(e.InnerException is OverflowException){threw=true;}
   Require(threw==check,"Overflow compilation option");context.Unload();
  }
  var bad=Compile("Public Module Broken\nPublic Function F() As Integer\nReturn\nEnd Function\nEnd Module","BadVB");
  Require(bad.GetDiagnostics().Any(d=>d.Severity==DiagnosticSeverity.Error),"Invalid source rejected");
  var error=bad.GetDiagnostics().First(d=>d.Severity==DiagnosticSeverity.Error);Require(error.GetMessage(CultureInfo.GetCultureInfo("fr"))!=error.GetMessage(CultureInfo.GetCultureInfo("en")),"Localized diagnostic lookup");
  GeneratorDriver driver=VisualBasicGeneratorDriver.Create(ImmutableArray.Create<ISourceGenerator>(new ProbeGenerator()));
  driver=driver.RunGeneratorsAndUpdateCompilation(Compile("Public Class Placeholder\nEnd Class","GeneratedVB"),out var updated,out var generatedDiagnostics);
  Require(!generatedDiagnostics.Any(d=>d.Severity==DiagnosticSeverity.Error)&&updated.GetTypeByMetadataName("GeneratedOwned")!=null,"Actual VB generator execution");
  using var generatedBytes=new MemoryStream();Require(updated.Emit(generatedBytes).Success,"Generated VB emits");generatedBytes.Position=0;
  var generatedContext=new AssemblyLoadContext("GeneratedVB",true);var generatedAssembly=generatedContext.LoadFromStream(generatedBytes);
  Require((int)generatedAssembly.GetType("GeneratedOwned").GetMethod("Value").Invoke(null,null)==73,"Generated VB IL execution");generatedContext.Unload();
  var withoutVb=references.Where(r=>!Path.GetFileName(r.FilePath).StartsWith("Microsoft.VisualBasic",StringComparison.OrdinalIgnoreCase)).ToArray();
  var embedded=Compile("Public Module EmbeddedOwned\nPublic Function F(s As String) As Integer\nReturn CInt(s)\nEnd Function\nEnd Module","EmbeddedVB",options.WithEmbedVbCoreRuntime(true),withoutVb);
  using var embeddedBytes=new MemoryStream();var embeddedResult=embedded.Emit(embeddedBytes);Require(embeddedResult.Success,"Embedded runtime templates: "+string.Join(";",embeddedResult.Diagnostics));embeddedBytes.Position=0;
  var embeddedContext=new AssemblyLoadContext("EmbeddedVB",true);var embeddedAssembly=embeddedContext.LoadFromStream(embeddedBytes);
  Require((int)embeddedAssembly.GetType("EmbeddedOwned").GetMethod("F").Invoke(null,new object[]{"42"})==42,"Embedded VB runtime conversion execution");
  Require(!embeddedAssembly.GetReferencedAssemblies().Any(a=>a.Name.StartsWith("Microsoft.VisualBasic")),"Embedded compilation has no normal VB runtime dependency");embeddedContext.Unload();
  using var cancellation=new CancellationTokenSource();cancellation.Cancel();bool canceled=false;try{compilation.GetDiagnostics(cancellation.Token);}catch(OperationCanceledException){canceled=true;}Require(canceled,"Compilation cancellation");
  foreach(System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)Require(!module.FileName.Replace('\\','/').Contains("/Microsoft.NET/Framework",StringComparison.OrdinalIgnoreCase),"Framework implementation loaded");
  Console.WriteLine("PASS checked/unchecked emitted arithmetic, errors and localized diagnostics, source generation, embedded VB runtime templates, cancellation and no Framework implementation");
 }
}
