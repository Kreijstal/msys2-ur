using System;
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

class Program
{
 static void Require(bool value,string message){if(!value)throw new Exception(message);}
 static async Task Main(string[] args)
 {
  CheckGenerated.Verify(args[3],args[4]);
  var analyzerAssembly=Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,"StyleCop.Analyzers.dll"));
  var fixAssembly=Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,"StyleCop.Analyzers.CodeFixes.dll"));
  foreach(var assembly in new[]{analyzerAssembly,fixAssembly})
  {
   Require(assembly.GetName().Version==new Version(1,2,0,556),"Assembly version");
   Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()).ToLowerInvariant()=="cfeb5dbada5e1c25","Assembly key");
   Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="1.2.0-beta.556+73a46ae2e65e7870fefe35e2c4c12bb7152f4ec5","Source identity");
  }
  using var inventory=JsonDocument.Parse(File.ReadAllText(args[0]));
  using var resources=JsonDocument.Parse(File.ReadAllText(args[1]));
  var analyzerTypes=analyzerAssembly.GetTypes().Where(t=>t.GetCustomAttributes<DiagnosticAnalyzerAttribute>().Any()).OrderBy(t=>t.FullName).ToArray();
  var fixTypes=fixAssembly.GetTypes().Where(t=>t.GetCustomAttributes<ExportCodeFixProviderAttribute>().Any()).OrderBy(t=>t.FullName).ToArray();
  Require(analyzerTypes.Select(t=>t.FullName).SequenceEqual(inventory.RootElement.GetProperty("analyzers").GetProperty("analyzers").EnumerateArray().Select(e=>e.GetString())),"All published analyzer classes");
  Require(fixTypes.Select(t=>t.FullName).SequenceEqual(inventory.RootElement.GetProperty("codefixes").GetProperty("code_fixes").EnumerateArray().Select(e=>e.GetString())),"All published code-fix classes");
  foreach(var pair in new[]{(name:"analyzers",assembly:analyzerAssembly),(name:"codefixes",assembly:fixAssembly)})
   Require(pair.assembly.GetManifestResourceNames().OrderBy(n=>n).SequenceEqual(inventory.RootElement.GetProperty(pair.name).GetProperty("resources").EnumerateArray().Select(e=>e.GetString())),"Published manifest resource inventory "+pair.name);
  var analyzers=analyzerTypes.ToDictionary(t=>t.FullName,t=>(DiagnosticAnalyzer)Activator.CreateInstance(t,true));
  var fixes=fixTypes.ToDictionary(t=>t.FullName,t=>(CodeFixProvider)Activator.CreateInstance(t,true));
  foreach(var entry in inventory.RootElement.GetProperty("analyzers").GetProperty("diagnostic_ids").EnumerateObject())
  {
   var type=analyzerAssembly.GetType(entry.Name);
   Require((string)type.GetField("DiagnosticId",BindingFlags.Static|BindingFlags.Public|BindingFlags.NonPublic).GetRawConstantValue()==entry.Value.GetString(),"Diagnostic ID "+entry.Name);
  }
  var descriptors=analyzers.Values.SelectMany(a=>a.SupportedDiagnostics).ToArray();
  var neutralStrings=resources.RootElement.EnumerateArray().Where(e=>e.GetProperty("culture").GetString()=="").SelectMany(e=>e.GetProperty("strings").EnumerateObject()).ToDictionary(e=>e.Name,e=>e.Value.GetString());
  foreach(var descriptor in descriptors)
  {
   Require(!string.IsNullOrEmpty(descriptor.Title.ToString()),"Descriptor title "+descriptor.Id);
   if(neutralStrings.TryGetValue(descriptor.Id+"Title",out string title))Require(descriptor.Title.ToString()==title,"Source descriptor title "+descriptor.Id);
   // Upstream's intentionally unimplemented rules have empty message formats.
   if(neutralStrings.TryGetValue(descriptor.Id+"MessageFormat",out string message))Require(descriptor.MessageFormat.ToString()==message,"Source descriptor format "+descriptor.Id);
  }
  foreach(var provider in fixes.Values)Require(!provider.FixableDiagnosticIds.IsEmpty,"Empty fix contract");
  int strings=0,sets=0;
  foreach(var entry in resources.RootElement.EnumerateArray())
  {
   string culture=entry.GetProperty("culture").GetString();var assembly=analyzerAssembly;
   if(culture.Length!=0)assembly=assembly.GetSatelliteAssembly(CultureInfo.GetCultureInfo(culture));
   string name=entry.GetProperty("resource").GetString()+(culture.Length==0?"":"."+culture)+".resources";
   using var reader=new ResourceReader(assembly.GetManifestResourceStream(name)??throw new Exception(name));
   var actual=reader.Cast<System.Collections.DictionaryEntry>().ToDictionary(e=>(string)e.Key,e=>(string)e.Value);
   Require(actual.Count==entry.GetProperty("strings").EnumerateObject().Count(),"Resource count "+name);
   foreach(var pair in entry.GetProperty("strings").EnumerateObject()){Require(actual.TryGetValue(pair.Name,out string value)&&value==pair.Value.GetString(),"Source resource "+name+"/"+pair.Name);strings++;}sets++;
  }
  Console.WriteLine($"PASS source assembly identities, {analyzers.Count} analyzer/{fixes.Count} fixer classes, {descriptors.Length} live descriptors and {sets} resource sets/{strings} strings");
  var references=Directory.GetFiles(args[2],"*.dll").Select(p=>MetadataReference.CreateFromFile(p)).ToArray();
  var host=MefHostServices.Create(new[]{typeof(Workspace).Assembly,typeof(CSharpFormattingOptions).Assembly});
  var allIds=descriptors.Select(d=>d.Id).Distinct().ToDictionary(id=>id,_=>ReportDiagnostic.Warn);
  ProjectInfo Info()=>ProjectInfo.Create(ProjectId.CreateNewId(),VersionStamp.Create(),"OwnedStyleCop","OwnedStyleCop",LanguageNames.CSharp,compilationOptions:new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary).WithSpecificDiagnosticOptions(allIds),parseOptions:new CSharpParseOptions(LanguageVersion.CSharp12,DocumentationMode.Diagnose),metadataReferences:references);
  using(var workspace=new AdhocWorkspace(host))
  {
   var project=workspace.AddProject(Info());
   var document=workspace.AddDocument(project.Id,"owned.cs",SourceText.From("using System;\nnamespace owned;\npublic record struct Pair(int x,int y);\npublic class sample { public int value { get; init; } public int M(){ var t=(first:1, second:2); return t.Item1; } }\n",Encoding.UTF8));
   var compilation=await document.Project.GetCompilationAsync();
   Require(!compilation.GetDiagnostics().Any(d=>d.Severity==DiagnosticSeverity.Error),"Owned sample compilation");
   var diagnostics=await compilation.WithAnalyzers(analyzers.Values.ToImmutableArray()).GetAnalyzerDiagnosticsAsync();
   Require(!diagnostics.Any(d=>d.Id=="AD0001"),"Analyzer exceptions: "+string.Join(";",diagnostics.Where(d=>d.Id=="AD0001")));
   Require(diagnostics.Any(d=>d.Id=="SA1142"),"Native IOperation-backed tuple analysis");
   Console.WriteLine($"PASS all analyzers execute on C# 12 records/file-scoped namespace/init/tuples without exceptions; {diagnostics.Select(d=>d.Id).Distinct().Count()} diagnostic IDs observed");
  }
  async Task Fix(string rule,string providerName,string input,string expected)
  {
   var analyzer=analyzers.Values.Single(a=>a.SupportedDiagnostics.Any(d=>d.Id==rule));
   var provider=fixes.Values.Single(f=>f.GetType().Name==providerName);
   using var workspace=new AdhocWorkspace(host);var project=workspace.AddProject(Info());
   var document=workspace.AddDocument(project.Id,"owned.cs",SourceText.From(input,Encoding.UTF8));
   for(int iteration=0;iteration<20;iteration++)
   {
    document=workspace.CurrentSolution.GetDocument(document.Id);var compilation=await document.Project.GetCompilationAsync();
    var diagnostics=await compilation.WithAnalyzers(ImmutableArray.Create(analyzer)).GetAnalyzerDiagnosticsAsync();
    Require(!diagnostics.Any(d=>d.Id=="AD0001"),"Fix analyzer exception");
    var diagnostic=diagnostics.FirstOrDefault(d=>d.Id==rule);if(diagnostic==null)break;
    var actions=new List<CodeAction>();await provider.RegisterCodeFixesAsync(new CodeFixContext(document,diagnostic,(a,_)=>actions.Add(a),CancellationToken.None));
    Require(actions.Count>0,"No action for "+rule);var action=actions[0];while(!action.NestedActions.IsEmpty)action=action.NestedActions[0];
    foreach(var operation in await action.GetOperationsAsync(CancellationToken.None))operation.Apply(workspace,CancellationToken.None);
   }
   document=workspace.CurrentSolution.GetDocument(document.Id);
   Require((await document.GetTextAsync()).ToString().Replace("\r","")==expected,"Exact fixed text "+rule+"\n"+(await document.GetTextAsync()));
   var final=await document.Project.GetCompilationAsync();Require(!(await final.WithAnalyzers(ImmutableArray.Create(analyzer)).GetAnalyzerDiagnosticsAsync()).Any(d=>d.Id==rule),"Rule remains after fix "+rule);
   Console.WriteLine("PASS real code-fix action, exact output and clean reanalysis: "+rule);
  }
  await Fix("SA1001","TokenSpacingCodeFixProvider","class C { int[] x = { 1,2 }; }\n","class C { int[] x = { 1, 2 }; }\n");
  await Fix("SA1142","SA1142CodeFixProvider","class C { int M() { var t = (first: 1, second: 2); return t.Item1; } }\n","class C { int M() { var t = (first: 1, second: 2); return t.first; } }\n");
  foreach(System.Diagnostics.ProcessModule module in System.Diagnostics.Process.GetCurrentProcess().Modules)Require(!module.FileName.Replace('\\','/').Contains("/Microsoft.NET/Framework",StringComparison.OrdinalIgnoreCase),"Framework implementation loaded");
  Console.WriteLine("PASS source identities/resources/all-analyzer probe and representative fixes; broader fixture/asset checks run separately");
 }
}
