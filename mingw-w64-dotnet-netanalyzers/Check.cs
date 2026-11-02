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
using Microsoft.CodeAnalysis.Diagnostics;
using Microsoft.CodeAnalysis.Formatting;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Simplification;
using Microsoft.CodeAnalysis.Text;
using Microsoft.CodeAnalysis.VisualBasic;
class Program
{
 static void Require(bool test,string message){if(!test)throw new Exception(message);}
 sealed class Options:AnalyzerConfigOptions
 {
  readonly Dictionary<string,string> values;
  public Options(Dictionary<string,string> values){this.values=values;}
  public override bool TryGetValue(string key,out string value)=>values.TryGetValue(key,out value);
  public override IEnumerable<string> Keys=>values.Keys;
 }
 sealed class Provider:AnalyzerConfigOptionsProvider
 {
  readonly Options options;
  public Provider(Dictionary<string,string> values){options=new Options(values);}
  public override AnalyzerConfigOptions GlobalOptions=>options;
  public override AnalyzerConfigOptions GetOptions(SyntaxTree tree)=>options;
  public override AnalyzerConfigOptions GetOptions(AdditionalText text)=>options;
 }
 static (string,List<TextSpan>) Markup(string input)
 {
  var text=new StringBuilder();var starts=new Stack<(int start,bool analyzer)>();var spans=new List<TextSpan>();
  for(int i=0;i<input.Length;i++)
  {
   if(i+1<input.Length&&input.Substring(i,2)=="{|") { int colon=input.IndexOf(':',i+2);Require(colon>=0,"Named markup header");string id=input.Substring(i+2,colon-i-2);starts.Push((text.Length,!System.Text.RegularExpressions.Regex.IsMatch(id,@"^(CS|BC)\d+$")));i=colon; }
   else if(i+1<input.Length&&input.Substring(i,2)=="|}") {Require(starts.Count>0,"Named markup close");var span=starts.Pop();if(span.analyzer)spans.Add(TextSpan.FromBounds(span.start,text.Length));i++;}
   else if(i+1<input.Length&&input.Substring(i,2)=="[|"){starts.Push((text.Length,true));i++;}
   else if(i+1<input.Length&&input.Substring(i,2)=="|]"){Require(starts.Count>0,"Unbalanced markup");var span=starts.Pop();if(span.analyzer)spans.Add(TextSpan.FromBounds(span.start,text.Length));i++;}
   else if(i+1<input.Length&&input.Substring(i,2)=="$$"){i++;}
   else text.Append(input[i]);
  }
  Require(starts.Count==0,"Unclosed markup");return(text.ToString(),spans);
 }
 static string Normalize(string s)=>s.Replace("\r\n","\n").Trim();
 static async Task Main(string[] args)
 {
  using var expected=JsonDocument.Parse(File.ReadAllText(args[0]));using var resources=JsonDocument.Parse(File.ReadAllText(args[1]));using var fixtures=JsonDocument.Parse(File.ReadAllText(args[2]));
  var assemblies=expected.RootElement.EnumerateObject().ToDictionary(a=>a.Name,n=>Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,n.Name)));
  var analyzers=new SortedDictionary<string,DiagnosticAnalyzer>();var fixes=new SortedDictionary<string,CodeFixProvider>();
  foreach(var entry in expected.RootElement.EnumerateObject())
  {
   var assembly=assemblies[entry.Name];Require(assembly.GetName().Version.ToString()=="8.0.14.27402","Original .NET analyzer assembly version");
   Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="31bf3856ad364e35","Original signing identity");
   Require(Path.GetFullPath(assembly.Location)==Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,entry.Name)),"Consumer-owned source assembly");
   Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="8.0.0-preview.26274.2+0963af6bfc2a3d5083faa2b7c1c91a4eee29a6f4","Source commit identity");
   var actualAnalyzers=assembly.GetTypes().Where(t=>!t.IsAbstract&&typeof(DiagnosticAnalyzer).IsAssignableFrom(t)&&t.GetCustomAttribute<DiagnosticAnalyzerAttribute>()!=null).ToArray();
   var actualFixers=assembly.GetTypes().Where(t=>!t.IsAbstract&&typeof(CodeFixProvider).IsAssignableFrom(t)&&t.GetCustomAttribute<ExportCodeFixProviderAttribute>()!=null).ToArray();
   Require(actualAnalyzers.Select(t=>t.FullName).OrderBy(n=>n).SequenceEqual(entry.Value.GetProperty("inventory").GetProperty("analyzers").EnumerateArray().Select(n=>n.GetString())),"Exact analyzer inventory "+entry.Name);
   Require(actualFixers.Select(t=>t.FullName).OrderBy(n=>n).SequenceEqual(entry.Value.GetProperty("inventory").GetProperty("code_fixes").EnumerateArray().Select(n=>n.GetString())),"Exact fixer inventory "+entry.Name);
   foreach(var type in actualAnalyzers)analyzers.Add(type.FullName,(DiagnosticAnalyzer)Activator.CreateInstance(type,true));
   foreach(var type in actualFixers)fixes.Add(type.FullName,(CodeFixProvider)Activator.CreateInstance(type,true));
  }
  Require(analyzers.Count==293&&fixes.Count==189,"Complete published analyzers/fixers");
  var legacyEmpty=new HashSet<string>(JsonDocument.Parse(File.ReadAllText(args[4])).RootElement.EnumerateArray().Select(e=>e.GetProperty("type").GetString()));
  var emptyTypes=new List<string>();
  foreach(var analyzer in analyzers.Values)
  {
   bool expectedEmpty=false;
   for(Type type=analyzer.GetType();type!=null;type=type.BaseType)if(legacyEmpty.Contains(type.FullName))expectedEmpty=true;
   Require(analyzer.SupportedDiagnostics.IsEmpty==expectedEmpty,"Original compatibility analyzer descriptor state "+analyzer.GetType().FullName);
   if(expectedEmpty)emptyTypes.Add(analyzer.GetType().FullName);
   foreach(var d in analyzer.SupportedDiagnostics)Require(d.Title.ToString().Length>0&&d.MessageFormat.ToString().Length>0,"Live descriptor resource "+d.Id);
  }
  Console.WriteLine("PASS original empty compatibility analyzer exports: "+emptyTypes.Count);

  var emptyFixers=new List<string>();
  foreach(var fixer in fixes.Values)
  {
   bool expectedEmpty=false;
   for(Type type=fixer.GetType();type!=null;type=type.BaseType)if(legacyEmpty.Contains(type.FullName))expectedEmpty=true;
   Require(fixer.FixableDiagnosticIds.IsEmpty==expectedEmpty,"Original compatibility fixer ID state "+fixer.GetType().FullName);
   if(expectedEmpty)emptyFixers.Add(fixer.GetType().FullName);
  }
  Console.WriteLine("PASS original empty compatibility fixer exports: "+emptyFixers.Count);

  int sets=0,strings=0;
  foreach(var entry in resources.RootElement.EnumerateArray())
  {
   var assembly=assemblies[entry.GetProperty("assembly").GetString()+".dll"];string culture=entry.GetProperty("culture").GetString();
   if(culture.Length!=0)assembly=assembly.GetSatelliteAssembly(CultureInfo.GetCultureInfo(culture));
   string name=entry.GetProperty("resource").GetString()+(culture.Length==0?"":"."+culture)+".resources";
   using var reader=new ResourceReader(assembly.GetManifestResourceStream(name)??throw new Exception(name));var values=reader.Cast<DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value);
   Require(values.Count==entry.GetProperty("strings").EnumerateObject().Count(),"Resource count "+name);
   foreach(var pair in entry.GetProperty("strings").EnumerateObject()){Require(values.TryGetValue(pair.Name,out var value)&&value==pair.Value.GetString(),"Resource value "+name+"/"+pair.Name);strings++;}sets++;
  }
  Console.WriteLine($"PASS all293 analyzers/189 fixers activated, original identities, live descriptors and {sets} resource sets/{strings} strings");
  var references=Directory.GetFiles(args[3],"*.dll").Select(p=>MetadataReference.CreateFromFile(p)).ToImmutableArray<MetadataReference>();
  var valuesConfig=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase){["build_property.EnforceCodeStyleInBuild"]="true",["build_property.EffectiveAnalysisLevelStyle"]="8.0"};
  var options=new AnalyzerOptions(ImmutableArray<AdditionalText>.Empty,new Provider(valuesConfig));int languageRuns=0;
  foreach(var entry in analyzers)
   foreach(string language in entry.Value.GetType().GetCustomAttribute<DiagnosticAnalyzerAttribute>().Languages)
   {
    bool vb=language==LanguageNames.VisualBasic;string source=vb?"Imports System\nClass Probe\n Private n As Integer = 1\n Function M(x As Integer) As Integer\n If x > 0 Then\n Return n + x\n Else\n Return 0\n End If\n End Function\nEnd Class":"using System; class Probe { private int n=1; int M(int x) { if(x>0) { return n+x; } else { return 0; } } }";
    var severities=entry.Value.SupportedDiagnostics.Select(d=>d.Id).Distinct().ToDictionary(id=>id,_=>ReportDiagnostic.Warn);
    Compilation compilation=vb?VisualBasicCompilation.Create("AllCallbacks",new[]{VisualBasicSyntaxTree.ParseText(source,path:"E:/owned/Probe.vb")},references,new VisualBasicCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(severities)):CSharpCompilation.Create("AllCallbacks",new[]{CSharpSyntaxTree.ParseText(source,path:"E:/owned/Probe.cs")},references,new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(severities));
    Require(!compilation.GetDiagnostics().Any(d=>d.Severity==DiagnosticSeverity.Error),"Owned callback probe must bind");
    var diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create(entry.Value),new CompilationWithAnalyzersOptions(options,null,true,false,true)).GetAnalyzerDiagnosticsAsync();
    Require(!diagnostics.Any(d=>d.Id=="AD0001"),"Analyzer callback exception: "+entry.Key+": "+string.Join("\n",diagnostics));languageRuns++;
   }
  Console.WriteLine("PASS every analyzer callback, "+languageRuns+" declared language combinations");
  var host=MefHostServices.Create(new[]{typeof(Workspace).Assembly,Assembly.Load("Microsoft.CodeAnalysis.CSharp.Workspaces"),Assembly.Load("Microsoft.CodeAnalysis.VisualBasic.Workspaces")});
  var passed=new List<string>();var failed=new List<string>();var exercised=new HashSet<string>();
  var legacyReferences=Directory.GetFiles(args[5],"*.dll").Select(p=>MetadataReference.CreateFromFile(p)).ToImmutableArray<MetadataReference>();
  foreach(var test in fixtures.RootElement.GetProperty("fixtures").EnumerateArray())
  {
   string title=test.GetProperty("label").GetString();
   try
   {
    string language=test.GetProperty("language").GetString();bool vb=language==LanguageNames.VisualBasic;var analyzer=analyzers[test.GetProperty("analyzer").GetString()];fixes.TryGetValue(test.GetProperty("fix").GetString(),out var fixer);
    var (source,spans)=Markup(test.GetProperty("source").GetString());
    using var workspace=new AdhocWorkspace(host);var project=workspace.AddProject("Owned",language).WithMetadataReferences(title.Contains("UseEnvironmentMembersTests.cs/")||title.Contains("UseCompositeFormatTests.cs/LacksTargetTypes")||title.Contains("SpecifyStringComparisonTests.cs/")?legacyReferences:references);
    var severities=analyzer.SupportedDiagnostics.Select(d=>d.Id).Distinct().ToDictionary(id=>id,_=>ReportDiagnostic.Warn);
    project=project.WithCompilationOptions(vb?new VisualBasicCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(severities):new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(severities));
    project=project.WithParseOptions(vb?new VisualBasicParseOptions(Microsoft.CodeAnalysis.VisualBasic.LanguageVersion.Latest):new CSharpParseOptions(Microsoft.CodeAnalysis.CSharp.LanguageVersion.CSharp12));
    var document=project.AddDocument(vb?"Probe.vb":"Probe.cs",SourceText.From(source),filePath:vb?"E:/owned/Probe.vb":"E:/owned/Probe.cs");
    var compilation=await document.Project.GetCompilationAsync();var diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create(analyzer),new CompilationWithAnalyzersOptions(options,null,true,false,true)).GetAnalyzerDiagnosticsAsync();
    Require(!diagnostics.Any(d=>d.Id=="AD0001"),"Analyzer exception: "+string.Join("\n",diagnostics));
    var ids=analyzer.SupportedDiagnostics.Select(d=>d.Id).ToHashSet();
    var candidates=diagnostics.Where(d=>ids.Contains(d.Id)).OrderBy(d=>d.Location.SourceSpan.Start).ThenBy(d=>d.Location.SourceSpan.Length).ToArray();
    int? expectedCount=test.TryGetProperty("expected_count",out var count)&&count.ValueKind==JsonValueKind.Number?count.GetInt32():(int?)null;
    int wantedCount=expectedCount??spans.Count;
    Require(candidates.Length==wantedCount,"Analyzer diagnostic count "+candidates.Length+" expected "+wantedCount+"; all="+string.Join("\n",diagnostics));
    if(spans.Count>0&&!(test.TryGetProperty("check_spans",out var checkSpans)&&!checkSpans.GetBoolean()))
     foreach(var span in spans)Require(candidates.Any(d=>span.IntersectsWith(d.Location.SourceSpan)),"Expected diagnostic span "+span);
    if(test.GetProperty("expected").ValueKind!=JsonValueKind.Null)
    {
     string wanted=Markup(test.GetProperty("expected").GetString()).Item1;
     int actionIndex=test.TryGetProperty("action_index",out var index)?index.GetInt32():0;int iterations=0;
     while(true)
     {
      if(iterations>0)
      {
       compilation=await document.Project.GetCompilationAsync();diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create(analyzer),new CompilationWithAnalyzersOptions(options,null,true,false,true)).GetAnalyzerDiagnosticsAsync();
       Require(!diagnostics.Any(d=>d.Id=="AD0001"),"Analyzer exception after code fix");
       candidates=diagnostics.Where(d=>fixer!=null&&fixer.FixableDiagnosticIds.Contains(d.Id)).OrderBy(d=>d.Location.SourceSpan.Length).ThenBy(d=>d.Location.SourceSpan.Start).ToArray();
      }
      CodeAction selected=null;
      foreach(var diagnostic in candidates)
      {
       if(fixer==null||!fixer.FixableDiagnosticIds.Contains(diagnostic.Id))continue;
       var actions=new List<CodeAction>();await fixer.RegisterCodeFixesAsync(new CodeFixContext(document,diagnostic,(a,_)=>actions.Add(a),CancellationToken.None));
       if(actions.Count>actionIndex){selected=actions[actionIndex];break;}
      }
      if(selected==null)break;
      var operation=(await selected.GetOperationsAsync(CancellationToken.None)).OfType<ApplyChangesOperation>().Single();var changed=operation.ChangedSolution.GetDocument(document.Id);Require(changed!=null,"Code fix deleted target document");
      changed=await Simplifier.ReduceAsync(changed,Simplifier.Annotation);changed=await Formatter.FormatAsync(changed,Formatter.Annotation);
      string before=(await document.GetTextAsync()).ToString();string actual=(await changed.GetTextAsync()).ToString();Require(actual!=before,"Code action made no progress");
      document=changed;exercised.Add(fixer.GetType().FullName);iterations++;Require(iterations<=100,"Code-fix iteration bound");
     }
     string result=(await document.GetTextAsync()).ToString();Require(Normalize(result)==Normalize(wanted),"Fixed text differs; actual="+result+" expected="+wanted);
    }
    passed.Add(title);
   }
   catch(Exception error){failed.Add(title+": "+error.Message);}
  }
  File.WriteAllText(Path.Combine(AppContext.BaseDirectory,"fixture-results.json"),JsonSerializer.Serialize(new{passed,failed,exercised_fixers=exercised.OrderBy(n=>n),languageRuns,resource_sets=sets,resource_strings=strings,empty_analyzers=emptyTypes,empty_fixers=emptyFixers},new JsonSerializerOptions{WriteIndented=true}));
  foreach(string failure in failed)Console.WriteLine("FAIL "+failure);
  Require(failed.Count==0,failed.Count+" upstream fixture failures");Require(passed.Count>=30&&exercised.Count>=8,"Meaningful selected upstream fixture/action coverage");
  Console.WriteLine($"PASS all{passed.Count} selected upstream/owned cases with actual actions from {exercised.Count} code-fix providers");
 }
}
