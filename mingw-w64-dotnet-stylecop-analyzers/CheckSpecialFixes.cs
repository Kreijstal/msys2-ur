using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CodeActions;
using Microsoft.CodeAnalysis.CodeFixes;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Formatting;
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Text;

static class CheckSpecialFixes
{
 static void Require(bool ok,string message){if(!ok)throw new Exception(message);}
 sealed class Diagnostics:FixAllContext.DiagnosticProvider
 {
  readonly DiagnosticAnalyzer analyzer;
  public Diagnostics(DiagnosticAnalyzer analyzer){this.analyzer=analyzer;}
  public override async Task<IEnumerable<Diagnostic>> GetDocumentDiagnosticsAsync(Document document,CancellationToken token)
  {
   var tree=await document.GetSyntaxTreeAsync(token);var all=await GetAllDiagnosticsAsync(document.Project,token);return all.Where(d=>d.Location.SourceTree==tree);
  }
  public override Task<IEnumerable<Diagnostic>> GetProjectDiagnosticsAsync(Project project,CancellationToken token)=>Task.FromResult(Enumerable.Empty<Diagnostic>());
  public override async Task<IEnumerable<Diagnostic>> GetAllDiagnosticsAsync(Project project,CancellationToken token)
  {var compilation=await project.GetCompilationAsync(token);return await compilation.WithAnalyzers(ImmutableArray.Create(analyzer)).GetAnalyzerDiagnosticsAsync(token);}
 }
 public static async Task<(string[] passed,Dictionary<string,string> failures,string[] providers)> Run(string refdir)
 {
  var assembly=Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,"StyleCop.Analyzers.dll"));
  var fixAssembly=Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,"StyleCop.Analyzers.CodeFixes.dll"));
  var all=assembly.GetTypes().Where(t=>t.GetCustomAttributes<DiagnosticAnalyzerAttribute>().Any()).Select(t=>(DiagnosticAnalyzer)Activator.CreateInstance(t,true)).ToArray();
  var references=Directory.GetFiles(refdir,"*.dll").Select(p=>MetadataReference.CreateFromFile(p)).ToArray();
  var host=MefHostServices.Create(new[]{typeof(Workspace).Assembly,typeof(CSharpFormattingOptions).Assembly});
  var passed=new List<string>();var failures=new Dictionary<string,string>();var covered=new HashSet<string>();
  async Task Test(string id,string providerName,string source,Func<Project,DocumentId,string,Task<bool>> verify,string name="Test0.cs",Encoding encoding=null,bool fixAll=false)
  {
   string label="owned:"+providerName+(fixAll?":FixAll":"");
   try
   {
    var analyzer=all.Single(a=>a.SupportedDiagnostics.Any(d=>d.Id==id));
    var providerType=fixAssembly.GetTypes().Single(t=>t.Name==providerName);var provider=(CodeFixProvider)Activator.CreateInstance(providerType,true);
    using var workspace=new AdhocWorkspace(host);
    var project=workspace.AddProject(ProjectInfo.Create(ProjectId.CreateNewId(),VersionStamp.Create(),"OwnedStructure","OwnedStructure",LanguageNames.CSharp,compilationOptions:new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(analyzer.SupportedDiagnostics.Select(d=>d.Id).Distinct().ToDictionary(d=>d,_=>ReportDiagnostic.Warn)),parseOptions:new CSharpParseOptions(LanguageVersion.CSharp12,DocumentationMode.Diagnose),metadataReferences:references));
    var document=workspace.AddDocument(project.Id,name,SourceText.From(source,encoding??Encoding.UTF8));
    var compilation=await document.Project.GetCompilationAsync();var diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create(analyzer)).GetAnalyzerDiagnosticsAsync();
    Require(!diagnostics.Any(d=>d.Id=="AD0001"),"Analyzer exception");
    Require(diagnostics.Any(d=>d.Id==id),"Missing initial "+id);
    bool applied=false;
    foreach(var diagnostic in diagnostics.Where(d=>d.Id==id))
    {
     var actions=new List<CodeAction>();await provider.RegisterCodeFixesAsync(new CodeFixContext(document,diagnostic,(a,_)=>actions.Add(a),CancellationToken.None));
     if(actions.Count==0)continue;var action=actions[0];while(!action.NestedActions.IsEmpty)action=action.NestedActions[0];
     if(fixAll)
     {
      Require(diagnostics.Count(d=>d.Id==id)>=2,"Multiple Fix All diagnostics");
      var context=new FixAllContext(document,provider,FixAllScope.Document,action.EquivalenceKey,provider.FixableDiagnosticIds,new Diagnostics(analyzer),CancellationToken.None);
      action=await provider.GetFixAllProvider().GetFixAsync(context);Require(action!=null,"Fix All action");
     }
     foreach(var operation in await action.GetOperationsAsync(CancellationToken.None))operation.Apply(workspace,CancellationToken.None);
     applied=true;break;
    }
    Require(applied,"No offered action");
    if(fixAll)
    {
     var final=await workspace.CurrentSolution.GetProject(project.Id).GetCompilationAsync();
     Require(!(await final.WithAnalyzers(ImmutableArray.Create(analyzer)).GetAnalyzerDiagnosticsAsync()).Any(d=>d.Id==id),"Fix All left target diagnostics");
    }
    Require(await verify(workspace.CurrentSolution.GetProject(project.Id),document.Id,source),"Structural result assertion\n"+string.Join("\n",await Task.WhenAll(workspace.CurrentSolution.GetProject(project.Id).Documents.Select(async d=>d.Name+"\n"+(await d.GetTextAsync()).ToString()))));
    passed.Add(label);covered.Add(providerType.FullName);Console.WriteLine("PASS "+label);
   }
   catch(Exception e){failures[label]=e.ToString();Console.WriteLine("FAIL "+label+": "+e.Message);}
  }
  static async Task<string> Text(Project p,DocumentId d)=>(await p.GetDocument(d).GetTextAsync()).ToString();
  await Test("SA1600","SA1600CodeFixProvider","public class C { public C() { } }\n",async(p,d,s)=>(await Text(p,d)).Contains("<summary>"));
  await Test("SA1600","InheritdocCodeFixProvider","/// <summary>Base type.</summary>\npublic class B {\n/// <summary>Runs.</summary>\npublic virtual void M() { } }\n/// <summary>Derived type.</summary>\npublic class C : B { public override void M() { } }\n",async(p,d,s)=>(await Text(p,d)).Contains("<inheritdoc"));
  await Test("SA1615","SA1615SA1616CodeFixProvider","public class C {\n/// <summary>Returns a value.</summary>\npublic int M() => 1; }\n",async(p,d,s)=>(await Text(p,d)).Contains("<returns>"));
  await Test("SA1649","SA1649CodeFixProvider","public class TestType { }\n",async(p,d,s)=>p.Documents.Single().Name=="TestType.cs"&&(await p.Documents.Single().GetTextAsync()).ToString()==s,"WrongFileName.cs");
  await Test("SA1518","SA1518CodeFixProvider","class C { }\n\n",async(p,d,s)=>(await Text(p,d)).Replace("\r","")=="class C { }\n");
  await Test("SA1400","SA1400CodeFixProvider","class C { }\n",async(p,d,s)=>(await Text(p,d)).Contains("internal class C"));
  await Test("SA1402","SA1402CodeFixProvider","class A { }\nclass B { }\n",async(p,d,s)=>p.Documents.Count()==2&&p.Documents.Any(x=>x.Name is "A.cs" or "B.cs")&&(await Task.WhenAll(p.Documents.Select(async x=>(await x.GetTextAsync()).ToString()))).All(t=>!(t.Contains("class A")&&t.Contains("class B"))));
  await Test("SA1404","SA1404CodeFixProvider","[System.Diagnostics.CodeAnalysis.SuppressMessage(\"category\", \"id\")]\nclass C { }\n",async(p,d,s)=>(await Text(p,d)).Contains("Justification"));
  await Test("SA1412","SA1412CodeFixProvider","class C { }\n",async(p,d,s)=>(await p.Documents.Single().GetTextAsync()).Encoding?.CodePage==Encoding.UTF8.CodePage&&(await p.Documents.Single().GetTextAsync()).ToString()==s,encoding:Encoding.ASCII);
  await Test("SA1308","SA1308CodeFixProvider","class C { int m_field; int M() => m_field; }\n",async(p,d,s)=>!(await Text(p,d)).Contains("m_field")&&(await Text(p,d)).Contains("=> field"));
  await Test("SA1316","SA1316CodeFixProvider","class C { (int first, int Second) M() => (1, 2); }\n",async(p,d,s)=>(await Text(p,d)).Contains("int First"));
  await Test("SX1309S","SX1309CodeFixProvider","class C { static int field; }\n",async(p,d,s)=>(await Text(p,d)).Contains("_field"));
  await Test("SA1600","SettingsFileCodeFixProvider","public class C { }\n",async(p,d,s)=>p.AdditionalDocuments.Count()==1&&p.AdditionalDocuments.Single().Name=="stylecop.json"&&(await p.AdditionalDocuments.Single().GetTextAsync()).ToString().Contains("documentationRules"));
  await Test("SA1018","SA1018CodeFixProvider","class C { int ? field; }\n",async(p,d,s)=>(await Text(p,d)).Contains("int? field"));
  await Test("SA1028","SA1028CodeFixProvider","class C { } \n",async(p,d,s)=>(await Text(p,d)).Replace("\r","")=="class C { }\n");
  await Test("SA1507","SA1507CodeFixProvider","class C\n{\n\n\n    void M() { }\n\n\n}\n",async(p,d,s)=>!(await Text(p,d)).Replace("\r","").Contains("\n\n\n"),fixAll:true);
  return(passed.ToArray(),failures,covered.OrderBy(x=>x).ToArray());
 }
}
