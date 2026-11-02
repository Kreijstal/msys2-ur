using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CodeActions;
using Microsoft.CodeAnalysis.CodeFixes;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Text;
using Microsoft.CodeAnalysis.VisualBasic;
partial class Program
{
 sealed class OwnedAdditional : AdditionalText
 {
  readonly string path;readonly SourceText text;
  public OwnedAdditional(string path,SourceText text){this.path=path;this.text=text;}
  public override string Path=>path;
  public override SourceText GetText(CancellationToken cancellationToken=default)=>text;
 }
 static async Task<ImmutableArray<Diagnostic>> AnalyzeOwned(Document document,DiagnosticAnalyzer analyzer)
 {
  var files=new List<AdditionalText>();
  foreach(var doc in document.Project.AdditionalDocuments)files.Add(new OwnedAdditional(doc.FilePath??doc.Name,await doc.GetTextAsync()));
  var result=await (await document.Project.GetCompilationAsync()).WithAnalyzers(ImmutableArray.Create(analyzer),new AnalyzerOptions(files.ToImmutableArray())).GetAnalyzerDiagnosticsAsync();
  Require(!result.Any(d=>d.Id=="AD0001"),"Owned structural analyzer exception: "+string.Join(";",result));return result;
 }
 static async Task ApplyOwned(AdhocWorkspace workspace,Document document,Diagnostic diagnostic,CodeFixProvider provider,HashSet<string> coveredFixes)
 {
  var actions=new List<CodeAction>();await provider.RegisterCodeFixesAsync(new CodeFixContext(document,diagnostic,(a,_)=>actions.Add(a),CancellationToken.None));
  Require(actions.Count>0,"Owned structural action registration "+diagnostic);
  var action=actions[0];while(!action.NestedActions.IsEmpty)action=action.NestedActions[0];
  foreach(var operation in await action.GetOperationsAsync(CancellationToken.None))operation.Apply(workspace,CancellationToken.None);
  coveredFixes.Add(provider.GetType().FullName);
 }
 sealed class OwnedFixAllDiagnostics : FixAllContext.DiagnosticProvider
 {
  readonly DocumentId id;readonly ImmutableArray<Diagnostic> diagnostics;public int Requests;
  public OwnedFixAllDiagnostics(DocumentId id,ImmutableArray<Diagnostic> diagnostics){this.id=id;this.diagnostics=diagnostics;}
  public override Task<IEnumerable<Diagnostic>> GetDocumentDiagnosticsAsync(Document document,CancellationToken token){Requests++;return Task.FromResult<IEnumerable<Diagnostic>>(document.Id==id?diagnostics:ImmutableArray<Diagnostic>.Empty);}
  public override Task<IEnumerable<Diagnostic>> GetProjectDiagnosticsAsync(Project project,CancellationToken token)=>Task.FromResult<IEnumerable<Diagnostic>>(ImmutableArray<Diagnostic>.Empty);
  public override Task<IEnumerable<Diagnostic>> GetAllDiagnosticsAsync(Project project,CancellationToken token){Requests++;return Task.FromResult<IEnumerable<Diagnostic>>(diagnostics);}
 }
 static async Task SpecialFixes(MefHostServices host,IEnumerable<MetadataReference> references,Dictionary<string,DiagnosticAnalyzer> analyzers,Dictionary<string,CodeFixProvider> fixes,HashSet<string> coveredFixes,List<string> passed)
 {
  foreach(bool vb in new[]{false,true})
  {
   string language=vb?LanguageNames.VisualBasic:LanguageNames.CSharp;
   Document Create(AdhocWorkspace workspace,string source,DiagnosticAnalyzer analyzer,string[] enabled)
   {
    var options=analyzer.SupportedDiagnostics.GroupBy(d=>d.Id).ToDictionary(g=>g.Key,g=>enabled.Contains(g.Key)?ReportDiagnostic.Warn:ReportDiagnostic.Suppress);
    CompilationOptions compilationOptions=vb?new VisualBasicCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(options):new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(options);
    var project=workspace.AddProject(ProjectInfo.Create(ProjectId.CreateNewId(),VersionStamp.Create(),"OwnedStructural","OwnedStructural",language,compilationOptions:compilationOptions,metadataReferences:references));
    return workspace.AddDocument(project.Id,vb?"owned.vb":"owned.cs",SourceText.From(source,Encoding.UTF8));
   }
   using(var workspace=new AdhocWorkspace(host))
   {
    var analyzer=analyzers["Microsoft.CodeAnalysis.Analyzers.MetaAnalyzers.PreferIsKindAnalyzer"];
    var provider=fixes[vb?"Microsoft.CodeAnalysis.VisualBasic.Analyzers.MetaAnalyzers.CodeFixes.BasicPreferIsKindFix":"Microsoft.CodeAnalysis.CSharp.Analyzers.MetaAnalyzers.Fixers.CSharpPreferIsKindFix"];
    string source=vb?"Imports Microsoft.CodeAnalysis\nImports Microsoft.CodeAnalysis.VisualBasic\nClass Owned\nFunction M(node As SyntaxNode) As Boolean\nReturn node.Kind() = SyntaxKind.None OrElse node.Kind() = SyntaxKind.TrueKeyword\nEnd Function\nEnd Class":"using Microsoft.CodeAnalysis; using Microsoft.CodeAnalysis.CSharp; class Owned { bool M(SyntaxNode node)=>node.Kind()==SyntaxKind.None || node.Kind()==SyntaxKind.TrueKeyword; }";
    var document=Create(workspace,source,analyzer,new[]{"RS1034"});var diagnostics=await AnalyzeOwned(document,analyzer);
    Require(diagnostics.Length==2&&diagnostics.All(d=>d.Id=="RS1034"),"Owned Fix All initial diagnostics");
    var actions=new List<CodeAction>();await provider.RegisterCodeFixesAsync(new CodeFixContext(document,diagnostics[0],(a,_)=>actions.Add(a),CancellationToken.None));
    Require(actions.Count>0,"Owned Fix All action key");var first=actions[0];while(!first.NestedActions.IsEmpty)first=first.NestedActions[0];
    var supplied=new OwnedFixAllDiagnostics(document.Id,diagnostics);
    var context=new FixAllContext(document,provider,FixAllScope.Document,first.EquivalenceKey,provider.FixableDiagnosticIds,supplied,CancellationToken.None);
    var action=await provider.GetFixAllProvider().GetFixAsync(context);Require(action!=null,"Actual original DocumentBasedFixAllProvider action");
    foreach(var operation in await action.GetOperationsAsync(CancellationToken.None))operation.Apply(workspace,CancellationToken.None);
    document=workspace.CurrentSolution.GetDocument(document.Id);string text=(await document.GetTextAsync()).ToString();
    Require(supplied.Requests>0&&text.Contains("IsKind")&&!text.Contains(".Kind()")&&(await AnalyzeOwned(document,analyzer)).Length==0,"Original helper fixes both nodes through actual Fix All diagnostic callbacks");
    coveredFixes.Add(provider.GetType().FullName);passed.Add("owned:PreferIsKindFixAll:"+language);
   }
   var descriptor=analyzers["Microsoft.CodeAnalysis.Analyzers.MetaAnalyzers.DiagnosticDescriptorCreationAnalyzer"];
   string DescriptorSource(bool malformed)=>vb?
    "Imports Microsoft.CodeAnalysis\nClass Owned\nPublic Shared ReadOnly Rule As New DiagnosticDescriptor(\"OWN0001\",\""+(malformed?"Title.":"Title")+"\",\"Message\",\"Category\",DiagnosticSeverity.Warning,True,description:=\"Description.\")\nEnd Class":
    "using Microsoft.CodeAnalysis; class Owned { public static readonly DiagnosticDescriptor Rule = new DiagnosticDescriptor(\"OWN0001\",\""+(malformed?"Title.":"Title")+"\",\"Message\",\"Category\",DiagnosticSeverity.Warning,true,description:\"Description.\"); }";
   using(var workspace=new AdhocWorkspace(host))
   {
    var document=Create(workspace,DescriptorSource(true),descriptor,new[]{"RS1031"});
    var diagnostics=await AnalyzeOwned(document,descriptor);Require(diagnostics.Length==1&&diagnostics[0].Id=="RS1031","Owned descriptor-title diagnostic");
    await ApplyOwned(workspace,document,diagnostics[0],fixes["Microsoft.CodeAnalysis.Analyzers.MetaAnalyzers.Fixers.DefineDiagnosticDescriptorArgumentsCorrectlyFix"],coveredFixes);
    document=workspace.CurrentSolution.GetDocument(document.Id);string text=(await document.GetTextAsync()).ToString();
    Require(text.Contains("\"Title\"")&&!text.Contains("\"Title.\"")&&(await AnalyzeOwned(document,descriptor)).Length==0,"Descriptor title fix changes the actual literal and removes RS1031");
    passed.Add("owned:DescriptorTitle:"+language);
   }
   using(var workspace=new AdhocWorkspace(host))
   {
    var document=Create(workspace,DescriptorSource(false),descriptor,new[]{"RS2000","RS2008"});
    var diagnostics=await AnalyzeOwned(document,descriptor);var enable=diagnostics.Single(d=>d.Id=="RS2008");
    var provider=fixes["Microsoft.CodeAnalysis.Analyzers.MetaAnalyzers.Fixers.AnalyzerReleaseTrackingFix"];
    await ApplyOwned(workspace,document,enable,provider,coveredFixes);document=workspace.CurrentSolution.GetDocument(document.Id);
    Require(document.Project.AdditionalDocuments.Select(d=>d.Name).OrderBy(n=>n).SequenceEqual(new[]{"AnalyzerReleases.Shipped.md","AnalyzerReleases.Unshipped.md"}),"Release fix adds both tracking documents");
    diagnostics=await AnalyzeOwned(document,descriptor);Require(!diagnostics.Any(d=>d.Id=="RS2008"),"Release tracking enabled");
    var declare=diagnostics.Single(d=>d.Id=="RS2000");await ApplyOwned(workspace,document,declare,provider,coveredFixes);
    document=workspace.CurrentSolution.GetDocument(document.Id);
    var unshipped=document.Project.AdditionalDocuments.Single(d=>d.Name=="AnalyzerReleases.Unshipped.md");string data=(await unshipped.GetTextAsync()).ToString();
    Require(data.Contains("OWN0001 | Category | Warning")&&(await AnalyzeOwned(document,descriptor)).Length==0,"Release fix writes a valid source-derived entry and removes RS2000");
    passed.Add("owned:ReleaseTrackingEnableAndEntry:"+language);
   }
   using(var workspace=new AdhocWorkspace(host))
   {
    var analyzer=analyzers["Microsoft.CodeAnalysis.Analyzers.FixAnalyzers.FixerWithFixAllAnalyzer"];
    string source=vb?
     "Imports System.Collections.Immutable\nImports System.Threading.Tasks\nImports Microsoft.CodeAnalysis.CodeFixes\nPublic Class OwnedFix\nInherits CodeFixProvider\nPublic Overrides ReadOnly Property FixableDiagnosticIds As ImmutableArray(Of String)\nGet\nReturn ImmutableArray.Create(\"OWN0001\")\nEnd Get\nEnd Property\nPublic Overrides Function RegisterCodeFixesAsync(context As CodeFixContext) As Task\nReturn Task.CompletedTask\nEnd Function\nEnd Class":
     "using System.Collections.Immutable; using System.Threading.Tasks; using Microsoft.CodeAnalysis.CodeFixes; public class OwnedFix:CodeFixProvider { public override ImmutableArray<string> FixableDiagnosticIds=>ImmutableArray.Create(\"OWN0001\"); public override Task RegisterCodeFixesAsync(CodeFixContext context)=>Task.CompletedTask; }";
    var document=Create(workspace,source,analyzer,new[]{"RS1016"});var diagnostics=await AnalyzeOwned(document,analyzer);
    Require(diagnostics.Length==1&&diagnostics[0].Id=="RS1016","Owned missing Fix All diagnostic");
    await ApplyOwned(workspace,document,diagnostics[0],fixes["Microsoft.CodeAnalysis.Analyzers.MetaAnalyzers.Fixers.FixerWithFixAllFix"],coveredFixes);
    document=workspace.CurrentSolution.GetDocument(document.Id);string text=(await document.GetTextAsync()).ToString();
    Require(text.Contains("GetFixAllProvider")&&text.Contains("WellKnownFixAllProviders.BatchFixer")&&(await AnalyzeOwned(document,analyzer)).Length==0,"Fix All override is generated and binds");
    var compilation=await document.Project.GetCompilationAsync();Require(!compilation.GetDiagnostics().Any(d=>d.Severity==DiagnosticSeverity.Error),"Generated Fix All provider must compile");
    passed.Add("owned:FixAllProviderOverride:"+language);
   }
  }
  Console.WriteLine("PASS owned C#/VB real PreferIsKind Fix All callbacks, descriptor literal fixes, release-tracking document creation/entry edits and generated Fix All overrides");
 }
}
