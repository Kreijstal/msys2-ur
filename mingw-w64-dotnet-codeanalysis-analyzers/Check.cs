using System;
using System.Collections;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
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
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Text;
using Microsoft.CodeAnalysis.VisualBasic;
partial class Program
{
 static void Require(bool value,string message){if(!value)throw new Exception(message);}
 static (string text,List<TextSpan> spans) Clean(string input)
 {
  var result=new StringBuilder();var spans=new List<TextSpan>();var stack=new Stack<(int start,bool diagnostic)>();
  for(int i=0;i<input.Length;)
  {
   if(input.AsSpan(i).StartsWith("[|")){stack.Push((result.Length,true));i+=2;continue;}
   if(input.AsSpan(i).StartsWith("{|"))
   {
    int end=input.IndexOf(':',i+2);Require(end>=0,"Named markup");string label=input.Substring(i+2,end-i-2);
    Require(label.Length>0&&label.All(c=>char.IsLetterOrDigit(c)||c=='#'),"Unexpected markup label");
    stack.Push((result.Length,label.StartsWith("RS")));i=end+1;continue;
   }
   if(input.AsSpan(i).StartsWith("|]")||input.AsSpan(i).StartsWith("|}"))
   {
    var mark=stack.Pop();if(mark.diagnostic)spans.Add(TextSpan.FromBounds(mark.start,result.Length));i+=2;continue;
   }
   if(input.AsSpan(i).StartsWith("$$")){i+=2;continue;}
   result.Append(input[i++]);
  }
  Require(stack.Count==0,"Unclosed markup");return(result.ToString(),spans);
 }
 static async Task Main(string[] args)
 {
  string[] names={"Microsoft.CodeAnalysis.Analyzers","Microsoft.CodeAnalysis.CSharp.Analyzers","Microsoft.CodeAnalysis.VisualBasic.Analyzers"};
  var assemblies=names.ToDictionary(n=>n,n=>Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,n+".dll")));
  using var inventory=JsonDocument.Parse(File.ReadAllText(args[0]));using var resources=JsonDocument.Parse(File.ReadAllText(args[1]));using var fixtureDoc=JsonDocument.Parse(File.ReadAllText(args[2]));
  foreach(var pair in assemblies)
  {
   var assembly=pair.Value;
   Require(assembly.GetName().Version==new Version(3,3,8,6701)&&Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="31bf3856ad364e35","Published assembly identity "+pair.Key);
   Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="3.3.4+22ea6422f85b05ca0793cc3b76375487be407f5d","Source identity");
   Require(Path.GetRelativePath(AppContext.BaseDirectory,assembly.Location)==pair.Key+".dll","Consumer-local source implementation");
   var actualAnalyzers=assembly.GetTypes().Where(t=>t.GetCustomAttributes<DiagnosticAnalyzerAttribute>(false).Any()).Select(t=>t.FullName).OrderBy(x=>x).ToArray();
   var actualFixes=assembly.GetTypes().Where(t=>t.GetCustomAttributes<ExportCodeFixProviderAttribute>(false).Any()).Select(t=>t.FullName).OrderBy(x=>x).ToArray();
   var expected=inventory.RootElement.GetProperty(pair.Key);
   Require(actualAnalyzers.SequenceEqual(expected.GetProperty("analyzers").EnumerateArray().Select(e=>e.GetString())),"Published analyzer classes "+pair.Key);
   Require(actualFixes.SequenceEqual(expected.GetProperty("code_fixes").EnumerateArray().Select(e=>e.GetString())),"Published code-fix classes "+pair.Key);
   foreach(var field in expected.GetProperty("diagnostic_ids").EnumerateObject())
   {
    int dot=field.Name.LastIndexOf('.');var type=assembly.GetType(field.Name.Substring(0,dot));
    Require((string)type.GetField(field.Name.Substring(dot+1),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).GetRawConstantValue()==field.Value.GetString(),"Published ID constant");
   }
  }
  var analyzers=assemblies.Values.SelectMany(a=>a.GetTypes()).Where(t=>t.GetCustomAttributes<DiagnosticAnalyzerAttribute>(false).Any()).ToDictionary(t=>t.FullName,t=>(DiagnosticAnalyzer)Activator.CreateInstance(t,true));
  var fixes=assemblies.Values.SelectMany(a=>a.GetTypes()).Where(t=>t.GetCustomAttributes<ExportCodeFixProviderAttribute>(false).Any()).ToDictionary(t=>t.FullName,t=>(CodeFixProvider)Activator.CreateInstance(t,true));
  Require(analyzers.Count==23&&fixes.Count==13,"Complete analyzer/code-fix payload");
  foreach(var analyzer in analyzers.Values)Require(analyzer.SupportedDiagnostics.Length>0&&analyzer.SupportedDiagnostics.All(d=>d.Id.StartsWith("RS")&&d.Title.ToString().Length>0&&d.MessageFormat.ToString().Length>0),"Live descriptor resources");
  foreach(var fix in fixes.Values)Require(fix.FixableDiagnosticIds.Length>0,"Nonempty code-fix contract");
  int sets=0,strings=0;
  foreach(var entry in resources.RootElement.EnumerateArray())
  {
   var assembly=assemblies[entry.GetProperty("assembly").GetString()];string culture=entry.GetProperty("culture").GetString();
   if(culture.Length!=0)assembly=assembly.GetSatelliteAssembly(CultureInfo.GetCultureInfo(culture));
   string name=entry.GetProperty("resource").GetString()+(culture.Length==0?"":"."+culture)+".resources";
   using var reader=new ResourceReader(assembly.GetManifestResourceStream(name)??throw new Exception(name));var values=reader.Cast<DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value);
   Require(values.Count==entry.GetProperty("strings").EnumerateObject().Count(),"Resource count");
   foreach(var pair in entry.GetProperty("strings").EnumerateObject()){Require(values.TryGetValue(pair.Name,out var value)&&value==pair.Value.GetString(),"Resource value "+pair.Name);strings++;}sets++;
  }
  Require(sets==14&&strings==2030,"Full neutral and translated resource inventory");
  Console.WriteLine($"PASS published identities, 23 analyzer/13 fixer/46 ID inventories, live descriptors and {sets} resource sets/{strings} strings");
  var references=Directory.GetFiles(args[3],"*.dll").Select(p=>MetadataReference.CreateFromFile(p)).ToList();
  foreach(var file in Directory.GetFiles(AppContext.BaseDirectory,"Microsoft.CodeAnalysis*.dll").Where(p=>!Path.GetFileName(p).EndsWith("Analyzers.dll")))references.Add(MetadataReference.CreateFromFile(file));
  references.Add(MetadataReference.CreateFromFile(Path.Combine(AppContext.BaseDirectory,"System.Composition.AttributedModel.dll")));
  var host=MefHostServices.Create(new[]{typeof(Workspace).Assembly,typeof(CSharpFormattingOptions).Assembly,Assembly.Load("Microsoft.CodeAnalysis.VisualBasic.Workspaces")});
  var passed=new List<string>();var failures=new List<string>();var coveredAnalyzers=new HashSet<string>();var coveredFixes=new HashSet<string>();var observed=new HashSet<string>();
  var executed=new HashSet<string>();int languageRuns=0;
  foreach(var entry in analyzers)
   foreach(var language in entry.Value.GetType().GetCustomAttribute<DiagnosticAnalyzerAttribute>(false).Languages)
   {
    bool vb=language==LanguageNames.VisualBasic;
    string source=vb?"Imports System.Collections.Immutable\nImports Microsoft.CodeAnalysis\nImports Microsoft.CodeAnalysis.Diagnostics\nClass Probe\n Inherits DiagnosticAnalyzer\n Public Overrides ReadOnly Property SupportedDiagnostics As ImmutableArray(Of DiagnosticDescriptor)\n Get\n Return ImmutableArray(Of DiagnosticDescriptor).Empty\n End Get\n End Property\n Public Overrides Sub Initialize(context As AnalysisContext)\n End Sub\nEnd Class": "using System.Collections.Immutable; using Microsoft.CodeAnalysis; using Microsoft.CodeAnalysis.Diagnostics; class Probe:DiagnosticAnalyzer { public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics => ImmutableArray<DiagnosticDescriptor>.Empty; public override void Initialize(AnalysisContext context){} }";
    var options=entry.Value.SupportedDiagnostics.GroupBy(d=>d.Id).ToDictionary(g=>g.Key,_=>ReportDiagnostic.Warn);
    Compilation compilation=vb?VisualBasicCompilation.Create("AllCallbacks",new[]{VisualBasicSyntaxTree.ParseText(source)},references,new VisualBasicCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(options)):CSharpCompilation.Create("AllCallbacks",new[]{CSharpSyntaxTree.ParseText(source)},references,new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(options));
    Require(!compilation.GetDiagnostics().Any(d=>d.Severity==DiagnosticSeverity.Error),"Owned all-analyzer probe must bind");
    var diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create(entry.Value)).GetAnalyzerDiagnosticsAsync();
    Require(!diagnostics.Any(d=>d.Id=="AD0001"),"Callback exception "+entry.Key+": "+string.Join(";",diagnostics));
    foreach(var diagnostic in diagnostics)observed.Add(diagnostic.Id);
    executed.Add(entry.Key);languageRuns++;
   }
  Require(executed.Count==23,"All analyzers execute");Console.WriteLine($"PASS all {executed.Count} source analyzers execute callbacks without exceptions across {languageRuns} declared language combinations");
  foreach(var fixture in fixtureDoc.RootElement.GetProperty("fixtures").EnumerateArray())
  {
   string label=fixture.GetProperty("label").GetString();
   try
   {
    var analyzer=analyzers[fixture.GetProperty("analyzer").GetString()];string language=fixture.GetProperty("language").GetString();bool vb=language==LanguageNames.VisualBasic;
    var options=analyzer.SupportedDiagnostics.GroupBy(d=>d.Id).ToDictionary(g=>g.Key,_=>ReportDiagnostic.Warn);
    CompilationOptions compilationOptions=vb?new VisualBasicCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(options):new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(options);
    bool modern=fixture.TryGetProperty("modern",out var modernValue)&&modernValue.GetBoolean();
    ParseOptions parse=vb?new VisualBasicParseOptions(Microsoft.CodeAnalysis.VisualBasic.LanguageVersion.VisualBasic15_5):new CSharpParseOptions(modern?Microsoft.CodeAnalysis.CSharp.LanguageVersion.CSharp12:Microsoft.CodeAnalysis.CSharp.LanguageVersion.CSharp7_3);
    using var workspace=new AdhocWorkspace(host);var project=workspace.AddProject(ProjectInfo.Create(ProjectId.CreateNewId(),VersionStamp.Create(),"OwnedAnalyzerInput","OwnedAnalyzerInput",language,compilationOptions:compilationOptions,parseOptions:parse,metadataReferences:references));
    if(fixture.TryGetProperty("additional_sources",out var additional))
     foreach(var text in additional.EnumerateArray()){var extra=workspace.AddDocument(project.Id,"extra"+Guid.NewGuid().ToString("N")+(vb?".vb":".cs"),SourceText.From(Clean(text.GetString()).text,Encoding.UTF8));project=extra.Project;}
    var input=Clean(fixture.GetProperty("source").GetString());var document=workspace.AddDocument(project.Id,vb?"owned.vb":"owned.cs",SourceText.From(input.text,Encoding.UTF8));
    var compilation=await document.Project.GetCompilationAsync();var diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create(analyzer)).GetAnalyzerDiagnosticsAsync();
    Require(!diagnostics.Any(d=>d.Id=="AD0001"),"Analyzer exception "+string.Join(";",diagnostics));
    int expectedCount=fixture.TryGetProperty("expected_count",out var countValue)&&countValue.ValueKind==JsonValueKind.Number?countValue.GetInt32():input.spans.Count;
    bool checkSpans=!fixture.TryGetProperty("check_spans",out var spanValue)||spanValue.GetBoolean();
    Require(diagnostics.Length==expectedCount,$"Diagnostic count expected={expectedCount} actual={diagnostics.Length}: "+string.Join(";",diagnostics));
    foreach(var diagnostic in diagnostics){observed.Add(diagnostic.Id);if(checkSpans)Require(input.spans.Contains(diagnostic.Location.SourceSpan),"Diagnostic span mismatch "+diagnostic);}
    coveredAnalyzers.Add(analyzer.GetType().FullName);
    if(fixture.GetProperty("expected").ValueKind!=JsonValueKind.Null)
    {
     var provider=fixes[fixture.GetProperty("fix").GetString()];string expected=Clean(fixture.GetProperty("expected").GetString()).text.Replace("\r","");
     for(int iteration=0;iteration<50;iteration++)
     {
      document=workspace.CurrentSolution.GetDocument(document.Id);compilation=await document.Project.GetCompilationAsync();
      var reported=await compilation.WithAnalyzers(ImmutableArray.Create(analyzer)).GetAnalyzerDiagnosticsAsync();Require(!reported.Any(d=>d.Id=="AD0001"),"Analyzer exception during code fix");bool changed=false;
      foreach(var diagnostic in reported.Where(d=>provider.FixableDiagnosticIds.Contains(d.Id)).OrderBy(d=>d.Location.SourceSpan.Start))
      {
       var actions=new List<CodeAction>();await provider.RegisterCodeFixesAsync(new CodeFixContext(document,diagnostic,(a,_)=>actions.Add(a),CancellationToken.None));if(actions.Count==0)continue;
       int actionIndex=fixture.TryGetProperty("action_index",out var indexValue)?indexValue.GetInt32():0;
       Require(actionIndex<actions.Count,"Configured code-action index");
       var action=actions[actionIndex];while(!action.NestedActions.IsEmpty)action=action.NestedActions[0];
       string before=(await document.GetTextAsync()).ToString();foreach(var operation in await action.GetOperationsAsync(CancellationToken.None))operation.Apply(workspace,CancellationToken.None);
       string after=(await workspace.CurrentSolution.GetDocument(document.Id).GetTextAsync()).ToString();
       if(before!=after){coveredFixes.Add(provider.GetType().FullName);changed=true;break;}
      }
      if(!changed)break;
     }
     string actual=(await workspace.CurrentSolution.GetDocument(document.Id).GetTextAsync()).ToString().Replace("\r","");
     Require(actual==expected,"Fixed text mismatch\nEXPECTED:\n"+expected+"\nACTUAL:\n"+actual);
    }
    passed.Add(label);
   }
   catch(Exception error){failures.Add(label+": "+error);Console.WriteLine("FAIL "+label+": "+error.Message);}
  }
  await SpecialFixes(host,references,analyzers,fixes,coveredFixes,passed);
  Require(coveredFixes.Count==13,"Every exported code-fix provider executes a passing action");
  File.WriteAllText(args[4],JsonSerializer.Serialize(new{passed,failures,executed_analyzers=executed.OrderBy(x=>x),language_runs=languageRuns,analyzers=coveredAnalyzers.OrderBy(x=>x),code_fixes=coveredFixes.OrderBy(x=>x),observed_ids=observed.OrderBy(x=>x)},new JsonSerializerOptions{WriteIndented=true}));
  Console.WriteLine($"Selected upstream/owned cases passed={passed.Count} failed={failures.Count}; analyzer coverage={coveredAnalyzers.Count}/23 code-fix action coverage={coveredFixes.Count}/13");
  Require(failures.Count==0,"Upstream fixture failures");
  foreach(System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)Require(!module.FileName.Replace('\\','/').Contains("/Microsoft.NET/Framework",StringComparison.OrdinalIgnoreCase),"Framework implementation loaded");
  Console.WriteLine("PASS selected original C#/VB diagnostic counts/spans and exact code-fix text; no Framework implementations");
 }
}
