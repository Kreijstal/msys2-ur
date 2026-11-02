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
  var text=new StringBuilder();var starts=new Stack<int>();var spans=new List<TextSpan>();
  for(int i=0;i<input.Length;i++)
  {
   if(i+1<input.Length&&input.Substring(i,2)=="[|"){starts.Push(text.Length);i++;}
   else if(i+1<input.Length&&input.Substring(i,2)=="|]"){Require(starts.Count>0,"Unbalanced markup");spans.Add(TextSpan.FromBounds(starts.Pop(),text.Length));i++;}
   else if(i+1<input.Length&&input.Substring(i,2)=="$$"){i++;}
   else text.Append(input[i]);
  }
  Require(starts.Count==0,"Unclosed markup");return(text.ToString(),spans);
 }
 static string Normalize(string s)=>s.Replace("\r\n","\n").Trim();
 static async Task Main(string[] args)
 {
  using var expected=JsonDocument.Parse(File.ReadAllText(args[0]));using var resources=JsonDocument.Parse(File.ReadAllText(args[1]));using var fixtures=JsonDocument.Parse(File.ReadAllText(args[2]));
  var assemblies=expected.RootElement.EnumerateObject().ToDictionary(a=>a.Name,n=>Assembly.Load(Path.GetFileNameWithoutExtension(n.Name)));
  var analyzers=new SortedDictionary<string,DiagnosticAnalyzer>();var fixes=new SortedDictionary<string,CodeFixProvider>();
  foreach(var entry in expected.RootElement.EnumerateObject())
  {
   var assembly=assemblies[entry.Name];Require(assembly.GetName().Version.ToString()=="4.9.10.12906","Original CodeStyle assembly version");
   Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="31bf3856ad364e35","Original signing identity");
   Require(Path.GetFullPath(assembly.Location)==Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,entry.Name)),"Consumer-owned source assembly");
   Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="4.9.2+9934fb9e3527e1c0c51314e57d4aab30f97e8f9e","Source commit identity");
   var actualAnalyzers=assembly.GetTypes().Where(t=>!t.IsAbstract&&typeof(DiagnosticAnalyzer).IsAssignableFrom(t)&&t.GetCustomAttribute<DiagnosticAnalyzerAttribute>()!=null).ToArray();
   var actualFixers=assembly.GetTypes().Where(t=>!t.IsAbstract&&typeof(CodeFixProvider).IsAssignableFrom(t)&&t.GetCustomAttribute<ExportCodeFixProviderAttribute>()!=null).ToArray();
   Require(actualAnalyzers.Select(t=>t.FullName).OrderBy(n=>n).SequenceEqual(entry.Value.GetProperty("inventory").GetProperty("analyzers").EnumerateArray().Select(n=>n.GetString())),"Exact analyzer inventory "+entry.Name);
   Require(actualFixers.Select(t=>t.FullName).OrderBy(n=>n).SequenceEqual(entry.Value.GetProperty("inventory").GetProperty("code_fixes").EnumerateArray().Select(n=>n.GetString())),"Exact fixer inventory "+entry.Name);
   foreach(var type in actualAnalyzers)analyzers.Add(type.FullName,(DiagnosticAnalyzer)Activator.CreateInstance(type,true));
   foreach(var type in actualFixers)fixes.Add(type.FullName,(CodeFixProvider)Activator.CreateInstance(type,true));
  }
  Require(analyzers.Count==135&&fixes.Count==172,"Complete published analyzers/fixers");
  foreach(var analyzer in analyzers.Values)Require(analyzer.SupportedDiagnostics.Length>0&&analyzer.SupportedDiagnostics.All(d=>(d.Title.ToString().Length>0&&d.MessageFormat.ToString().Length>0)||(d.Id=="RemoveUnnecessaryImportsFixable"&&d.Title.ToString()==""&&d.MessageFormat.ToString()=="")),"Live descriptors/resources "+analyzer.GetType().FullName+": "+string.Join(";",analyzer.SupportedDiagnostics.Select(d=>d.Id+"/"+d.Title.ToString()+"/"+d.MessageFormat.ToString())));
  foreach(var fixer in fixes.Values)Require(fixer.FixableDiagnosticIds.Length>0,"Nonempty fixer contract");
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
  Console.WriteLine($"PASS all135 analyzers/172 fixers activated, original identities, live descriptors and {sets} resource sets/{strings} strings");
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
  foreach(var test in fixtures.RootElement.GetProperty("cases").EnumerateArray())
  {
   string title=test.GetProperty("file").GetString()+"::"+test.GetProperty("method").GetString();
   try
   {
    string language=test.GetProperty("language").GetString();bool vb=language==LanguageNames.VisualBasic;var analyzer=analyzers[test.GetProperty("analyzer").GetString()];var fixer=fixes[test.GetProperty("fixer").GetString()];
    var (source,spans)=Markup(test.GetProperty("source").GetString());
    using var workspace=new AdhocWorkspace(host);var project=workspace.AddProject("Owned",language).WithMetadataReferences(references);
    var severities=analyzer.SupportedDiagnostics.Select(d=>d.Id).Distinct().ToDictionary(id=>id,_=>ReportDiagnostic.Warn);
    project=project.WithCompilationOptions(vb?new VisualBasicCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(severities):new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(severities));
    project=project.WithParseOptions(vb?new VisualBasicParseOptions(Microsoft.CodeAnalysis.VisualBasic.LanguageVersion.Latest):new CSharpParseOptions(Microsoft.CodeAnalysis.CSharp.LanguageVersion.CSharp12));
    var document=project.AddDocument(vb?"Probe.vb":"Probe.cs",SourceText.From(source),filePath:vb?"E:/owned/Probe.vb":"E:/owned/Probe.cs");
    var compilation=await document.Project.GetCompilationAsync();var diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create(analyzer),new CompilationWithAnalyzersOptions(options,null,true,false,true)).GetAnalyzerDiagnosticsAsync();
    Require(!diagnostics.Any(d=>d.Id=="AD0001"),"Analyzer exception: "+string.Join("\n",diagnostics));
    var candidates=diagnostics.Where(d=>fixer.FixableDiagnosticIds.Contains(d.Id)&&(spans.Count==0||spans.Any(s=>s.IntersectsWith(d.Location.SourceSpan)))).OrderBy(d=>d.Location.SourceSpan.Start).ToArray();
    if(test.GetProperty("missing").GetBoolean())Require(candidates.Length==0,"Unexpected diagnostic at selected target: "+string.Join("\n",candidates.Select(d=>d.ToString())));
    else
    {
     Require(candidates.Length>0,"Missing targeted analyzer diagnostic; all="+string.Join("\n",diagnostics));
     var actions=new List<CodeAction>();await fixer.RegisterCodeFixesAsync(new CodeFixContext(document,candidates[0],(a,_)=>actions.Add(a),CancellationToken.None));Require(actions.Count>0,"No actual code-fix action");
     var operation=(await actions[0].GetOperationsAsync(CancellationToken.None)).OfType<ApplyChangesOperation>().Single();var changed=operation.ChangedSolution.GetDocument(document.Id);Require(changed!=null,"Code fix deleted target document");
     changed=await Simplifier.ReduceAsync(changed,Simplifier.Annotation);changed=await Formatter.FormatAsync(changed,Formatter.Annotation);
     string actual=(await changed.GetTextAsync()).ToString();string wanted=Markup(test.GetProperty("expected").GetString()).Item1;
     Require(Normalize(actual)==Normalize(wanted),"Fixed text differs; actual="+actual+" expected="+wanted);exercised.Add(fixer.GetType().FullName);
    }
    passed.Add(title);
   }
   catch(Exception error){failed.Add(title+": "+error.Message);}
  }
  File.WriteAllText(Path.Combine(AppContext.BaseDirectory,"fixture-results.json"),JsonSerializer.Serialize(new{passed,failed,exercised_fixers=exercised.OrderBy(n=>n),languageRuns,resource_sets=sets,resource_strings=strings},new JsonSerializerOptions{WriteIndented=true}));
  foreach(string failure in failed)Console.WriteLine("FAIL "+failure);
  Require(failed.Count==0,failed.Count+" upstream fixture failures");Require(passed.Count>=30&&exercised.Count>=8,"Meaningful selected upstream fixture/action coverage");
  Console.WriteLine($"PASS all{passed.Count} selected upstream cases with actual actions from {exercised.Count} code-fix providers");
 }
}
