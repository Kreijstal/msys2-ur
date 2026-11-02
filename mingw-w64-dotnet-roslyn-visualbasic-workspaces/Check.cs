using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Composition;
using System.Composition.Hosting;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CodeActions;
using Microsoft.CodeAnalysis.CodeFixes;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Formatting;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Editing;
using Microsoft.CodeAnalysis.FindSymbols;
using Microsoft.CodeAnalysis.Formatting;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Rename;
using Microsoft.CodeAnalysis.Simplification;
using Microsoft.CodeAnalysis.Text;
using Microsoft.CodeAnalysis.VisualBasic;
using Microsoft.CodeAnalysis.VisualBasic.Syntax;
using VBFactory=Microsoft.CodeAnalysis.VisualBasic.SyntaxFactory;

[DiagnosticAnalyzer(LanguageNames.VisualBasic)]
public sealed class LowerNameAnalyzer : DiagnosticAnalyzer
{
 public static readonly DiagnosticDescriptor Rule=new("VBW001","Capitalize class","Capitalize '{0}'","Workspace test",DiagnosticSeverity.Warning,true);
 public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics=>ImmutableArray.Create(Rule);
 public override void Initialize(AnalysisContext context)
 {
  context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);context.EnableConcurrentExecution();
  context.RegisterSyntaxNodeAction(c=>{var node=(ClassStatementSyntax)c.Node;if(char.IsLower(node.Identifier.ValueText[0]))c.ReportDiagnostic(Diagnostic.Create(Rule,node.Identifier.GetLocation(),node.Identifier.ValueText));},Microsoft.CodeAnalysis.VisualBasic.SyntaxKind.ClassStatement);
 }
}
public sealed class UpperNameFix : CodeFixProvider
{
 public override ImmutableArray<string> FixableDiagnosticIds=>ImmutableArray.Create("VBW001");
 public override FixAllProvider GetFixAllProvider()=>WellKnownFixAllProviders.BatchFixer;
 public override Task RegisterCodeFixesAsync(CodeFixContext context)
 {
  context.RegisterCodeFix(CodeAction.Create("Capitalize",async token=>{
   var editor=await DocumentEditor.CreateAsync(context.Document,token);
   var node=editor.OriginalRoot.FindToken(context.Span.Start).Parent.AncestorsAndSelf().OfType<ClassStatementSyntax>().First();
   string name=node.Identifier.ValueText;
   editor.ReplaceNode(node,node.WithIdentifier(VBFactory.Identifier(char.ToUpperInvariant(name[0])+name.Substring(1)).WithTriviaFrom(node.Identifier)));
   return editor.GetChangedDocument();
  },"capitalize-owned-vb-class"),context.Diagnostics);return Task.CompletedTask;
 }
}
class Program
{
 const string Name="Microsoft.CodeAnalysis.VisualBasic.Workspaces";
 static void Require(bool value,string message){if(!value)throw new Exception(message);}
 static Assembly Source(string resourcePath,string itemsPath)
 {
  var assembly=Assembly.Load(new AssemblyName(Name));
  Require(assembly.GetName().Version==new Version(4,9,0,0)&&Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="31bf3856ad364e35","Assembly identity");
  Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version=="4.9.2.0"&&assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="4.9.2+9934fb9e3527e1c0c51314e57d4aab30f97e8f9e","Source identity");
  Require(Path.GetRelativePath(AppContext.BaseDirectory,assembly.Location)==Name+".dll","Source consumer assembly location");
  using var source=JsonDocument.Parse(File.ReadAllText(itemsPath));
  var inventory=source.RootElement.GetProperty(Name);
  Require(inventory.GetProperty("source_files").GetInt32()==234&&inventory.GetProperty("source_paths").GetArrayLength()==234&&inventory.GetProperty("imports").GetArrayLength()==3,"Original full source inventory");
  var wanted=inventory.GetProperty("friends").EnumerateArray().Select(x=>x.GetString()).OrderBy(x=>x).ToArray();
  var actual=assembly.GetCustomAttributes<InternalsVisibleToAttribute>().Select(x=>x.AssemblyName).OrderBy(x=>x).ToArray();
  Require(wanted.SequenceEqual(actual)&&actual.Length==19&&actual.All(x=>!x.Contains("$(")&&x.Contains("PublicKey=")),"Original expanded friend declarations");
  Require(!assembly.GetReferencedAssemblies().Any(r=>r.Name.StartsWith("Microsoft.VisualBasic")),"Embedded VB runtime support only");
  // Workspaces language implementations are internal MEF services: public API alone is not a completeness gate.
  Require(assembly.GetExportedTypes().Length==0,"Expected internal language-service implementation assembly");
  using var entries=JsonDocument.Parse(File.ReadAllText(resourcePath));int sets=0,strings=0;
  foreach(var entry in entries.RootElement.EnumerateArray())
  {
   Require(entry.GetProperty("assembly").GetString()==Name,"Resource assembly");
   string culture=entry.GetProperty("culture").GetString();var satellite=culture.Length==0?assembly:assembly.GetSatelliteAssembly(CultureInfo.GetCultureInfo(culture));
   string name=entry.GetProperty("resource").GetString()+(culture.Length==0?"":"."+culture)+".resources";
   using var reader=new ResourceReader(satellite.GetManifestResourceStream(name)??throw new Exception(name));
   var values=reader.Cast<DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value);
   Require(values.Count==entry.GetProperty("strings").EnumerateObject().Count(),"Resource count "+name);
   foreach(var pair in entry.GetProperty("strings").EnumerateObject()){Require(values.TryGetValue(pair.Name,out var value)&&value==pair.Value.GetString(),"Source translation "+name+"/"+pair.Name);strings++;}sets++;
  }
  Require(sets==42&&strings==756,"Complete neutral/XLF manifest");
  Console.WriteLine("PASS exact source identity, 234 source inputs, 19 friend declarations, embedded VB support and 42 resource sets/756 strings");return assembly;
 }
 static void Errors(Compilation compilation)
 {
  var errors=compilation.GetDiagnostics().Where(d=>d.Severity==DiagnosticSeverity.Error).ToArray();
  Require(errors.Length==0,string.Join("\n",errors.Select(d=>d.ToString())));
 }
 static byte[] Emit(Compilation compilation)
 {
  Errors(compilation);using var stream=new MemoryStream();var result=compilation.Emit(stream);
  Require(result.Success,string.Join("\n",result.Diagnostics));return stream.ToArray();
 }
 static async Task Main(string[] args)
 {
  var vb=Source(args[0],args[1]);
  using var container=new ContainerConfiguration().WithAssemblies(new[]{typeof(Workspace).Assembly,vb,typeof(CSharpFormattingOptions).Assembly}).CreateContainer();
  var host=MefHostServices.Create(container);
  using var workspace=new AdhocWorkspace(host);
  Require(workspace.Services.SupportedLanguages.Contains(LanguageNames.VisualBasic)&&workspace.Services.SupportedLanguages.Contains(LanguageNames.CSharp),"MEF language services");
  var exports=vb.GetTypes().SelectMany(t=>t.GetCustomAttributes<ExportAttribute>(inherit:false).Select(a=>(Type:t,Attribute:a))).ToArray();
  var activated=exports.SelectMany(e=>container.GetExports(e.Attribute.ContractType)).Select(o=>o.GetType()).ToHashSet();
  if(exports.Length!=48||!exports.All(e=>activated.Contains(e.Type)))
   foreach(var e in exports)Console.WriteLine($"EXPORT {e.Type.FullName} ATTRIBUTE {e.Attribute.GetType().FullName} ACTIVATED {activated.Contains(e.Type)}");
  Require(exports.Length==48&&exports.All(e=>activated.Contains(e.Type)),"Every VB MEF export activates; count="+exports.Length);
  int languageServices=0;
  var services=workspace.Services.GetLanguageServices(LanguageNames.VisualBasic);
  var getter=typeof(Microsoft.CodeAnalysis.Host.HostLanguageServices).GetMethods().Single(m=>m.Name=="GetService"&&m.IsGenericMethodDefinition);
  foreach(var export in exports)
  {
   string service=export.Attribute switch { ExportLanguageServiceAttribute a=>a.ServiceType,ExportLanguageServiceFactoryAttribute a=>a.ServiceType,_=>null };
   if(service==null)continue;
   var value=getter.MakeGenericMethod(Type.GetType(service,true)).Invoke(services,null);
   Require(value!=null&&value.GetType().Assembly==vb,"VB language-service/factory activation: "+service);languageServices++;
  }
  Require(languageServices==41,"Full 33 service / eight factory inventory");
  Console.WriteLine($"PASS every one of {exports.Length} MEF export parts activates and all 41 VB language services/factories resolve");
  var references=Directory.GetFiles(args[2],"*.dll").Select(f=>MetadataReference.CreateFromFile(f)).ToArray();
  ProjectId library=ProjectId.CreateNewId(),client=ProjectId.CreateNewId();
  var solution=workspace.CurrentSolution.AddProject(ProjectInfo.Create(library,VersionStamp.Create(),"OwnedVbLibrary","OwnedVbLibrary",LanguageNames.VisualBasic,compilationOptions:new VisualBasicCompilationOptions(OutputKind.DynamicallyLinkedLibrary),parseOptions:new VisualBasicParseOptions(Microsoft.CodeAnalysis.VisualBasic.LanguageVersion.Latest),metadataReferences:references))
   .AddProject(ProjectInfo.Create(client,VersionStamp.Create(),"OwnedCsClient","OwnedCsClient",LanguageNames.CSharp,compilationOptions:new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary),parseOptions:new CSharpParseOptions(Microsoft.CodeAnalysis.CSharp.LanguageVersion.CSharp12),metadataReferences:references,projectReferences:new[]{new ProjectReference(library)}));
  var libDoc=DocumentId.CreateNewId(library);var clientDoc=DocumentId.CreateNewId(client);
  solution=solution.AddDocument(libDoc,"math-π.vb",SourceText.From("Namespace OwnedLib\nPublic Module Calc\nPublic Function Add(a As Integer,b As Integer) As Integer\nReturn a+b\nEnd Function\nPublic Function OwnRun() As Integer\nReturn aDd(10,11)\nEnd Function\nEnd Module\nEnd Namespace\n",Encoding.UTF8))
   .AddDocument(clientDoc,"client.cs",SourceText.From("public class Entry{public static int Run()=>OwnedLib.Calc.Add(20,22);}",Encoding.UTF8));
  Require(workspace.TryApplyChanges(solution),"Initial solution changes");
  var compilation=await workspace.CurrentSolution.GetProject(library).GetCompilationAsync();Errors(compilation);
  var method=(IMethodSymbol)compilation.GetTypeByMetadataName("OwnedLib.Calc").GetMembers("Add").Single();
  var found=(await SymbolFinder.FindReferencesAsync(method,workspace.CurrentSolution)).SelectMany(x=>x.Locations).ToArray();
  Require(found.Length==2&&found.Any(x=>x.Document.Id==clientDoc)&&found.Any(x=>x.Document.Id==libDoc),"Cross-language and case-insensitive VB references");
  solution=await Renamer.RenameSymbolAsync(workspace.CurrentSolution,method,new SymbolRenameOptions(),"Sum");
  Require(workspace.TryApplyChanges(solution),"Semantic rename changes");
  string libraryText=(await workspace.CurrentSolution.GetDocument(libDoc).GetTextAsync()).ToString();
  Require(libraryText.Contains("Function Sum")&&libraryText.Contains("Sum(10,11)")&&(await workspace.CurrentSolution.GetDocument(clientDoc).GetTextAsync()).ToString().Contains("Calc.Sum"),"Cross-language rename and case-insensitive VB references");
  var formatted=await Formatter.FormatAsync(workspace.CurrentSolution.GetDocument(libDoc));
  Require((await formatted.GetTextAsync()).ToString().Contains("Public Function Sum(a As Integer, b As Integer) As Integer"),"VB formatting service");
  Require(workspace.TryApplyChanges(formatted.Project.Solution),"Apply VB formatting");
  byte[] libBytes=Emit(await workspace.CurrentSolution.GetProject(library).GetCompilationAsync());
  byte[] clientBytes=Emit(await workspace.CurrentSolution.GetProject(client).GetCompilationAsync());
  var load=new AssemblyLoadContext("Owned workspace emission",true);
  try
  {
   var lib=load.LoadFromStream(new MemoryStream(libBytes));load.Resolving+=(context,name)=>name.Name=="OwnedVbLibrary"?lib:null;
   var cs=load.LoadFromStream(new MemoryStream(clientBytes));
   Require((int)lib.GetType("OwnedLib.Calc").GetMethod("OwnRun").Invoke(null,null)==21,"Execute renamed/formatted VB");
   Require((int)cs.GetType("Entry").GetMethod("Run").Invoke(null,null)==42,"Execute cross-language project reference");
  }
  finally{load.Unload();}
  Console.WriteLine("PASS MEF VB/CSharp workspaces, Unicode documents, case-insensitive/cross-language reference search and rename, VB formatting, project-reference emit and executed IL");
  var fixId=DocumentId.CreateNewId(library);solution=workspace.CurrentSolution.AddDocument(fixId,"fix.vb",SourceText.From("Public Class lower\nPrivate Name As Global.System.String = \"owned\"\nEnd Class\n",Encoding.UTF8));
  Require(workspace.TryApplyChanges(solution),"Add code-fix source");
  var doc=workspace.CurrentSolution.GetDocument(fixId);
  doc=doc.WithSyntaxRoot((await doc.GetSyntaxRootAsync()).WithAdditionalAnnotations(Simplifier.Annotation));
  var simplified=await Simplifier.ReduceAsync(doc);
  Require((await simplified.GetTextAsync()).ToString().Contains("As String"),"VB simplification service");
  Require(workspace.TryApplyChanges(simplified.Project.Solution),"Apply simplified document");
  doc=workspace.CurrentSolution.GetDocument(fixId);compilation=await doc.Project.GetCompilationAsync();Errors(compilation);
  var diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create<DiagnosticAnalyzer>(new LowerNameAnalyzer())).GetAnalyzerDiagnosticsAsync();
  var diagnostic=diagnostics.Single(d=>d.Id=="VBW001");CodeAction action=null;
  await new UpperNameFix().RegisterCodeFixesAsync(new CodeFixContext(doc,diagnostic,(a,_)=>action=a,CancellationToken.None));Require(action!=null,"Analyzer code-action registration");
  foreach(var operation in await action.GetOperationsAsync(CancellationToken.None))operation.Apply(workspace,CancellationToken.None);
  Require((await workspace.CurrentSolution.GetDocument(fixId).GetTextAsync()).ToString().Contains("Class Lower"),"CodeAction edits VB workspace");
  doc=workspace.CurrentSolution.GetDocument(fixId);
  var editor=await DocumentEditor.CreateAsync(doc);var generator=editor.Generator;
  var block=editor.OriginalRoot.DescendantNodes().OfType<ClassBlockSyntax>().Single();
  var field=generator.FieldDeclaration("Added",generator.TypeExpression(SpecialType.System_Int32),Accessibility.Public,DeclarationModifiers.Static,generator.LiteralExpression(73));
  editor.AddMember(block,field);doc=await Formatter.FormatAsync(editor.GetChangedDocument());
  Require(workspace.TryApplyChanges(doc.Project.Solution),"Apply generated VB field");
  compilation=await workspace.CurrentSolution.GetProject(library).GetCompilationAsync();
  var added=compilation.GetTypeByMetadataName("Lower").GetMembers("Added").OfType<IFieldSymbol>().Single();
  Require(added.IsStatic&&added.Type.SpecialType==SpecialType.System_Int32,"VB SyntaxGenerator/DocumentEditor semantics");
  byte[] edited=Emit(compilation);var editedLoad=new AssemblyLoadContext("Edited VB",true);
  try{var result=editedLoad.LoadFromStream(new MemoryStream(edited));Require((int)result.GetType("Lower").GetField("Added").GetValue(null)==73,"Execute VB SyntaxGenerator field");}finally{editedLoad.Unload();}
  var old=workspace.CurrentSolution;var changed=old.WithDocumentText(fixId,SourceText.From("Public Class Lower\nEnd Class\n",Encoding.UTF8));
  Require(changed.GetChanges(old).GetProjectChanges().Single().GetChangedDocuments().Single()==fixId,"Incremental solution change tracking");
  using var cancelled=new CancellationTokenSource();cancelled.Cancel();
  try{await SymbolFinder.FindReferencesAsync(method,changed,cancelled.Token);throw new Exception("Cancellation accepted");}catch(OperationCanceledException){}
  foreach(System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)
   Require(!module.FileName.Replace('\\','/').Contains("/Microsoft.NET/Framework",StringComparison.OrdinalIgnoreCase),"Framework implementation loaded");
  Console.WriteLine("PASS VB simplification, real analyzer/code-fix actions, DocumentEditor/SyntaxGenerator with executed output, incremental edits, cancellation and no Framework implementations");
 }
}
